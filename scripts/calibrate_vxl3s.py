#!/usr/bin/env python3
"""Interactively calibrate a Traxxas VXL-3s to the JetRacer PWM output.

This follows the VXL-3s setup-programming sequence with the Jetson/PCA9685
acting as the transmitter.  Disconnect motor wires A and C and keep the driven
wheels raised before starting.  The ESC output is returned to neutral on normal
exit, Ctrl-C, SIGTERM, or terminal disconnect.

Run on the Jetson:
    ~/jr/bin/python ~/JetRacer-JetPack7/scripts/calibrate_vxl3s.py
"""

import argparse
import signal

from jetracer.nvidia_racecar import NvidiaRacecar


def pulse_us(car, channel):
    pca = car.kit._pca
    return round(pca.channels[channel].duty_cycle / 65535 * 1e6 / pca.frequency)


def wait_for_enter(message):
    input(f"\n{message}\nPress Enter to continue... ")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steering-channel", type=int, default=1)
    parser.add_argument("--esc-channel", type=int, default=2)
    parser.add_argument(
        "--endpoint-amount",
        type=float,
        default=1.0,
        help="absolute JetRacer throttle command used as each calibration endpoint (default: 1.0)",
    )
    args = parser.parse_args()

    if args.steering_channel == args.esc_channel:
        parser.error("steering and ESC channels must be different")
    if not 0 <= args.steering_channel <= 15 or not 0 <= args.esc_channel <= 15:
        parser.error("PCA9685 channels must be between 0 and 15")
    if not 0 < args.endpoint_amount <= 1:
        parser.error("--endpoint-amount must be greater than 0 and no more than 1")

    car = NvidiaRacecar(
        steering_channel=args.steering_channel,
        throttle_channel=args.esc_channel,
    )
    car.steering = 0.0
    car.throttle = 0.0

    def stop_on_signal(signum, _frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGINT, stop_on_signal)
    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGHUP, stop_on_signal)

    print("VXL-3s / Jetson endpoint calibration")
    print(f"Neutral is active: ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us")

    try:
        confirmation = input(
            "\nTurn the ESC OFF, disconnect motor wires A and C, and keep the wheels raised.\n"
            "Type CALIBRATE when that is done: "
        )
        if confirmation.strip() != "CALIBRATE":
            print("Calibration cancelled.")
            return

        wait_for_enter(
            "With neutral still active, press and HOLD the ESC EZ-Set button. "
            "Release it after the LED changes from green to red. Wait until the LED blinks RED ONCE."
        )

        car.throttle = args.endpoint_amount
        print(
            f"FULL FORWARD active: throttle {args.endpoint_amount:+.2f}, "
            f"ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us"
        )
        wait_for_enter("Keep full forward active until the LED blinks RED TWICE.")

        car.throttle = -args.endpoint_amount
        print(
            f"FULL REVERSE active: throttle {-args.endpoint_amount:+.2f}, "
            f"ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us"
        )
        wait_for_enter("Keep full reverse active until the LED blinks GREEN ONCE.")

        car.throttle = 0.0
        print(f"Calibration sequence complete; ESC neutral is {pulse_us(car, args.esc_channel)} us.")
        print("The ESC LED should now be solid green or solid red, not blinking.")
    except (EOFError, KeyboardInterrupt) as exc:
        print(f"\nCalibration interrupted: {exc}")
    finally:
        car.throttle = 0.0
        car.steering = 0.0
        print(
            f"Safe stop: steering ch{args.steering_channel} {pulse_us(car, args.steering_channel)} us, "
            f"ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us"
        )


if __name__ == "__main__":
    main()
