#!/usr/bin/env python3
"""Interactive WASD control for the AGX Orin JetRacer.

Hardware mapping discovered on this car:
    steering servo = PCA9685 channel 1
    Traxxas VXL-3s ESC = PCA9685 channel 2

The ESC is not yet calibrated for ordinary proportional throttle.  Pressing W
therefore runs one complete 1645/1352 us diagnostic sequence that was verified
to accelerate this car.  Pressing S/Space, losing the terminal, or exiting
always returns the ESC to neutral.

Run in a real terminal with all driven wheels off the ground:
    ~/jr/bin/python ~/JetRacer-JetPack7/scripts/wasd_control.py
"""

import argparse
import os
import select
import signal
import sys
import termios
import time
import tty


ESC_SEQUENCE = (0.195, -0.195, 0.195, -0.195)


class CarOutput:
    def __init__(self, steering_channel, esc_channel, dry_run=False):
        self.dry_run = dry_run
        self.steering_channel = steering_channel
        self.esc_channel = esc_channel
        self.steering = 0.0
        self.esc_motor_throttle = 0.0
        self.car = None
        self.racecar_type = None

        if not dry_run:
            from jetracer.nvidia_racecar import NvidiaRacecar

            self.racecar_type = NvidiaRacecar
        self.reinitialize()

    def reinitialize(self):
        """Recreate ServoKit, matching the fresh process used by the working test."""
        if self.car is not None:
            try:
                self.car.kit._pca.deinit()
            except Exception:
                pass
            self.car = None

        if self.racecar_type is not None:
            self.car = self.racecar_type(
                steering_channel=self.steering_channel,
                throttle_channel=self.esc_channel,
            )
        self.neutral_all()

    def set_steering(self, value):
        self.steering = value
        if self.car is not None:
            self.car.steering = value

    def set_esc_motor_throttle(self, value):
        """Set the ContinuousServo-level ESC value used by the verified sequence."""
        self.esc_motor_throttle = value
        if self.car is not None:
            # NvidiaRacecar applies throttle_gain in its observer.  Divide it
            # back out so +/-0.195 produces the verified 1645/1352 us pulses.
            self.car.throttle = value / self.car.throttle_gain

    def neutral_esc(self):
        self.set_esc_motor_throttle(0.0)

    def neutral_all(self):
        self.neutral_esc()
        self.set_steering(0.0)

    def pulse_us(self, channel):
        if self.car is None:
            if channel == self.esc_channel:
                return round(1498 + self.esc_motor_throttle * 750)
            return 1498
        pca = self.car.kit._pca
        return round(pca.channels[channel].duty_cycle / 65535 * 1e6 / pca.frequency)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steering-channel", type=int, default=1)
    parser.add_argument("--esc-channel", type=int, default=2)
    parser.add_argument("--steering-amount", type=float, default=0.3)
    parser.add_argument("--esc-step-seconds", type=float, default=1.0)
    parser.add_argument(
        "--key-release-timeout",
        type=float,
        default=0.8,
        help="centre steering after A/D key repeat stops",
    )
    parser.add_argument("--dry-run", action="store_true", help="exercise keyboard handling without touching hardware")
    args = parser.parse_args()

    if args.steering_channel == args.esc_channel:
        parser.error("steering and ESC channels must be different")
    if not 0 <= args.steering_channel <= 15 or not 0 <= args.esc_channel <= 15:
        parser.error("PCA9685 channels must be between 0 and 15")
    if not 0 < args.steering_amount <= 1:
        parser.error("--steering-amount must be between 0 and 1")
    if args.esc_step_seconds <= 0 or args.key_release_timeout <= 0:
        parser.error("timing values must be positive")
    return args


def status(output, drive_active, message):
    drive = "W sequence" if drive_active else "neutral"
    line = (
        f"{message:<24} | steering {output.steering:+.2f} ch{output.steering_channel} "
        f"| ESC {drive} {output.pulse_us(output.esc_channel)} us ch{output.esc_channel}"
    )
    print(f"\r\x1b[2K{line}", end="", flush=True)


def main():
    args = parse_args()
    if not sys.stdin.isatty():
        raise SystemExit("wasd_control.py must run in an interactive terminal")

    output = CarOutput(args.steering_channel, args.esc_channel, args.dry_run)
    fd = sys.stdin.fileno()
    original_terminal = termios.tcgetattr(fd)
    drive_active = False
    sequence_index = 0
    next_sequence_step = 0.0
    last_steering_key = float("-inf")

    def stop_on_signal(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGINT, stop_on_signal)
    signal.signal(signal.SIGHUP, stop_on_signal)

    print("WASD control (wheels OFF the ground)")
    print("W=one acceleration burst  A=left  D=right  S=neutral  Space=all stop  C=center  Q=quit")
    if args.dry_run:
        print("DRY RUN: hardware output disabled")

    try:
        tty.setcbreak(fd)
        status(output, drive_active, "ready")

        while True:
            now = time.monotonic()
            readable, _, _ = select.select([fd], [], [], 0.05)
            if readable:
                key = os.read(fd, 1).decode(errors="ignore").lower()
                now = time.monotonic()

                if key == "q":
                    status(output, drive_active, "quitting")
                    break
                if key == "w":
                    if not drive_active:
                        # The verified manual test constructs NvidiaRacecar and
                        # starts the sequence immediately.  Recreate ServoKit
                        # here as well; waiting at neutral left the VXL-3s in
                        # its green-blinking lockout on this car.
                        output.reinitialize()
                        drive_active = True
                        sequence_index = 0
                        output.set_esc_motor_throttle(ESC_SEQUENCE[sequence_index])
                        next_sequence_step = now + args.esc_step_seconds
                        status(output, drive_active, "W burst started")
                    else:
                        status(output, drive_active, "W burst already active")
                elif key == "a":
                    last_steering_key = now
                    output.set_steering(-args.steering_amount)
                    status(output, drive_active, "left")
                elif key == "d":
                    last_steering_key = now
                    output.set_steering(args.steering_amount)
                    status(output, drive_active, "right")
                elif key == "c":
                    output.set_steering(0.0)
                    last_steering_key = float("-inf")
                    status(output, drive_active, "steering centered")
                elif key in ("s", " "):
                    drive_active = False
                    output.neutral_esc()
                    if key == " ":
                        output.set_steering(0.0)
                        last_steering_key = float("-inf")
                    status(output, drive_active, "ALL STOP" if key == " " else "ESC neutral")

            now = time.monotonic()
            if drive_active and now >= next_sequence_step:
                if sequence_index == len(ESC_SEQUENCE) - 1:
                    drive_active = False
                    output.neutral_esc()
                    status(output, drive_active, "W burst complete")
                else:
                    sequence_index += 1
                    output.set_esc_motor_throttle(ESC_SEQUENCE[sequence_index])
                    next_sequence_step = now + args.esc_step_seconds
                    status(output, drive_active, f"W step {sequence_index + 1}/4")

            if output.steering != 0.0 and now - last_steering_key > args.key_release_timeout:
                output.set_steering(0.0)
                status(output, drive_active, "steering centered")
    except KeyboardInterrupt:
        pass
    finally:
        output.neutral_all()
        termios.tcsetattr(fd, termios.TCSADRAIN, original_terminal)
        print("\nStopped: steering centered and ESC neutral.")


if __name__ == "__main__":
    main()
