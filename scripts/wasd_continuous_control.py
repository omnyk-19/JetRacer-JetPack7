#!/usr/bin/env python3
"""Hold-to-drive WASD control for the AGX Orin JetRacer (VXL-3s).

The ESC on this car has not accepted ordinary proportional throttle. Its only
physically verified acceleration command is a four-step sequence with a fresh
ServoKit initialization before every cycle. The default verified mode repeats
that exact sequence while W remains held:

  1. Hold W: recreate ServoKit and send +0.195, -0.195, +0.195, -0.195,
     holding every value for one second; repeat from a fresh initialization.
  2. Release W: immediately cancel the cycle and return the ESC to neutral.
  3. A/D steer, S/Space stop, and focus loss stops and centres the car.

Use --mode steady only after the ESC has been calibrated and a steady forward
command has been physically validated. Up/Down trim applies to steady mode.

Wheels OFF the ground for first hardware tests.
    ~/jr/bin/python wasd_continuous_control.py [--dry-run]
    ~/jr/bin/python wasd_continuous_control.py --self-test
"""
import argparse
import json
import signal
from pathlib import Path

CONFIG = Path.home() / ".jetracer_esc.json"
RELEASE_DEBOUNCE_MS = 80
ESC_SEQUENCE = (0.195, -0.195, 0.195, -0.195)


class CarOutput:
    """Fail-safe steering and ESC output used by the verified WASD controller."""

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
            # NvidiaRacecar applies throttle_gain in its observer. Divide it
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


class ClockedOutput(CarOutput):
    """CarOutput + optional PCA9685 reference-clock correction (see esc_neutral_finder.py)."""

    def __init__(self, *args, clock_hz=None, **kwargs):
        self.clock_hz = clock_hz
        super().__init__(*args, **kwargs)

    def reinitialize(self):
        super().reinitialize()
        if self.car is not None and self.clock_hz:
            pca = self.car.kit._pca
            pca.reference_clock_speed = self.clock_hz
            pca.frequency = 50  # recompute prescale for the corrected clock


def load_clock(arg):
    if arg:
        return arg
    try:
        return json.loads(CONFIG.read_text())["reference_clock_speed"]
    except (OSError, KeyError, ValueError):
        return None


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--steering-channel", type=int, default=1)
    p.add_argument("--esc-channel", type=int, default=2)
    p.add_argument("--steering-amount", type=float, default=0.3)
    p.add_argument("--throttle", type=float, default=0.195, help="steady forward level, motor units (0.195 = 1645 us)")
    p.add_argument("--max-throttle", type=float, default=0.30)
    p.add_argument("--step-seconds", type=float, default=1.0, help="wake-up sequence step length")
    p.add_argument("--settle-seconds", type=float, default=0.4, help="neutral after wake-up")
    p.add_argument("--mode", choices=["verified", "steady", "pulse"], default="verified",
                   help="verified: repeat the exact working four-step sequence; steady: experimental constant forward; "
                        "pulse is a compatibility alias for verified")
    p.add_argument("--forward-seconds", type=float, default=1.0, help=argparse.SUPPRESS)
    p.add_argument("--brake-seconds", type=float, default=0.2, help=argparse.SUPPRESS)
    p.add_argument("--no-arm", action="store_true", help="steady mode only: skip its initial four-step sequence")
    p.add_argument("--rearm-each-press", action="store_true",
                   help="steady mode only: repeat its initial sequence on every W press")
    p.add_argument("--clock-hz", type=int, help="PCA9685 reference clock (default: from ~/.jetracer_esc.json)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--self-test", action="store_true", help="exercise WASD logic without opening a GUI or hardware")
    p.add_argument("--demo", action="store_true", help="automated GUI WASD exercise; requires --dry-run")
    a = p.parse_args()
    if a.steering_channel == a.esc_channel:
        p.error("steering and ESC channels must differ")
    if not 0 <= a.steering_channel <= 15 or not 0 <= a.esc_channel <= 15:
        p.error("PCA9685 channels must be between 0 and 15")
    if not 0 < a.steering_amount <= 1:
        p.error("--steering-amount must be between 0 and 1")
    if not 0 < a.throttle <= a.max_throttle <= 0.5:
        p.error("need 0 < --throttle <= --max-throttle <= 0.5")
    if min(a.step_seconds, a.settle_seconds, a.forward_seconds, a.brake_seconds) <= 0:
        p.error("all timing values must be positive")
    if a.clock_hz is not None and a.clock_hz <= 0:
        p.error("--clock-hz must be positive")
    if a.demo and not a.dry_run:
        p.error("--demo is only available with --dry-run")
    return a


class Controller:
    def __init__(self, root, args):
        self.root, self.args = root, args
        clock = load_clock(args.clock_hz)
        self.output = ClockedOutput(args.steering_channel, args.esc_channel, args.dry_run, clock_hz=clock)
        self.clock = clock
        self.throttle = args.throttle
        self.armed = args.no_arm
        self.state = "idle"  # idle | arming | settling | driving
        self.seq_index = 0
        self.after_id = None
        self.pressed, self.pending_releases = set(), {}
        self.closed = False
        self.build_ui()
        self.set_status("Click the window, then hold W. Wheels must be off the ground.")

    # ---------- UI ----------
    def build_ui(self):
        import tkinter as tk

        r = self.root
        r.title("JetRacer continuous control")
        r.geometry("720x330")
        r.configure(bg="#151a20")
        r.protocol("WM_DELETE_WINDOW", self.close)
        r.bind_all("<KeyPress>", self.on_key_press)
        r.bind_all("<KeyRelease>", self.on_key_release)
        r.bind("<FocusOut>", lambda e: self.emergency_stop("Focus lost: ALL STOP"))
        drive_description = "experimental steady forward" if self.args.mode == "steady" else "verified 4-step cycles"
        tk.Label(r, text=f"Hold W: {drive_description}   A/D: steer   Up/Down: trim speed\n"
                         "S/Space: stop   C: centre   Q/Esc: exit",
                 font=("Sans", 14), fg="white", bg="#151a20").pack(pady=18)
        self.status_var, self.detail_var = tk.StringVar(), tk.StringVar()
        tk.Label(r, textvariable=self.status_var, font=("Monospace", 14), fg="#f0c674",
                 bg="#151a20", wraplength=680).pack(pady=14)
        tk.Label(r, textvariable=self.detail_var, font=("Monospace", 12), fg="#c5c8c6", bg="#151a20").pack()
        r.after(100, r.focus_force)
        r.after(100, self.heartbeat)
        if self.args.demo:
            self.schedule_demo()

    def heartbeat(self):
        if not self.closed:
            self.root.after(100, self.heartbeat)

    def set_status(self, msg):
        self.status_var.set(msg)
        o = self.output
        self.detail_var.set(f"state={self.state}  armed={self.armed}  throttle={self.throttle:+.3f}  "
                            f"ESC={o.pulse_us(o.esc_channel)}us  steer={o.steering:+.2f}  "
                            f"clock={self.clock or 'nominal'}")
        if self.args.dry_run:
            print(msg, flush=True)

    # ---------- keys ----------
    def on_key_press(self, event):
        key = event.keysym.lower()
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            self.root.after_cancel(pending)
        if key not in self.pressed:
            self.press(key)

    def on_key_release(self, event):
        key = event.keysym.lower()
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            self.root.after_cancel(pending)
        self.pending_releases[key] = self.root.after(RELEASE_DEBOUNCE_MS, lambda: self.release(key))

    def press(self, key):
        self.pressed.add(key)
        if key == "w":
            self.start_w()
        elif key in ("a", "d"):
            self.apply_steering()
        elif key in ("up", "down"):
            self.trim(0.01 if key == "up" else -0.01)
        elif key in ("s", "space"):
            self.emergency_stop("STOP")
        elif key == "c":
            self.pressed -= {"a", "d"}
            self.apply_steering()
        elif key in ("q", "escape"):
            self.close()

    def release(self, key):
        self.pending_releases.pop(key, None)
        self.pressed.discard(key)
        if key == "w":
            self.stop_drive("W released: neutral")
        elif key in ("a", "d"):
            self.apply_steering()

    def apply_steering(self):
        left, right = "a" in self.pressed, "d" in self.pressed
        value = 0.0 if left == right else (-self.args.steering_amount if left else self.args.steering_amount)
        self.output.set_steering(value)
        self.set_status("steering %+.2f" % value)

    def trim(self, delta):
        if self.args.mode != "steady":
            self.set_status("speed trim is available only in --mode steady")
            return
        self.throttle = round(min(self.args.max_throttle, max(0.05, self.throttle + delta)), 3)
        if self.state == "driving":
            self.output.set_esc_motor_throttle(self.throttle)
        self.set_status("throttle trimmed")

    # ---------- drive state machine ----------
    def start_w(self):
        if self.state != "idle" or self.closed:
            return
        if self.args.mode in ("verified", "pulse"):
            self.start_verified_cycle()
            return
        if not self.armed or self.args.rearm_each_press:
            self.start_arm()
        else:
            self.start_drive()

    def schedule(self, seconds, fn):
        self.after_id = self.root.after(round(seconds * 1000), fn)

    def start_arm(self):
        self.output.reinitialize()  # the verified wake-up used a fresh ServoKit
        self.apply_steering()
        self.state, self.seq_index = "arming", 0
        self.output.set_esc_motor_throttle(ESC_SEQUENCE[0])
        self.set_status("W: wake-up step 1/4")
        self.schedule(self.args.step_seconds, self.advance_arm)

    def advance_arm(self):
        self.after_id = None
        if "w" not in self.pressed or self.closed:
            self.armed = False
            self.stop_drive("W released during wake-up: not armed")
            return
        if self.seq_index < len(ESC_SEQUENCE) - 1:
            self.seq_index += 1
            self.output.set_esc_motor_throttle(ESC_SEQUENCE[self.seq_index])
            self.set_status(f"W: wake-up step {self.seq_index + 1}/4")
            self.schedule(self.args.step_seconds, self.advance_arm)
        else:
            self.output.neutral_esc()
            self.state = "settling"
            self.set_status("wake-up done, neutral settle")
            self.schedule(self.args.settle_seconds, self.finish_arm)

    def finish_arm(self):
        self.after_id = None
        self.armed = True
        self.state = "idle"
        if "w" in self.pressed and not self.closed:
            self.start_drive()
        else:
            self.set_status("armed; hold W to drive")

    def start_drive(self):
        self.state = "driving"
        self.apply_steering()
        self.output.set_esc_motor_throttle(self.throttle)
        self.set_status("DRIVING: experimental steady forward")

    def start_verified_cycle(self):
        if "w" not in self.pressed or self.closed:
            return
        self.output.reinitialize()
        self.apply_steering()
        self.state, self.seq_index = "driving", 0
        self.output.set_esc_motor_throttle(ESC_SEQUENCE[0])
        self.set_status("W held: verified step 1/4")
        self.schedule(self.args.step_seconds, self.advance_verified_cycle)

    def advance_verified_cycle(self):
        self.after_id = None
        if "w" not in self.pressed or self.closed or self.state != "driving":
            self.stop_drive("W released: neutral")
            return
        if self.seq_index < len(ESC_SEQUENCE) - 1:
            self.seq_index += 1
            self.output.set_esc_motor_throttle(ESC_SEQUENCE[self.seq_index])
            self.set_status(f"W held: verified step {self.seq_index + 1}/4")
            self.schedule(self.args.step_seconds, self.advance_verified_cycle)
            return

        # Reinitialization before every cycle is required by the only waveform
        # that has physically accelerated this VXL-3s installation.
        self.start_verified_cycle()

    def stop_drive(self, msg):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.state = "idle"
        self.output.neutral_esc()
        self.set_status(msg)

    def emergency_stop(self, msg):
        if self.closed:
            return
        self.pressed.clear()
        for cb in self.pending_releases.values():
            self.root.after_cancel(cb)
        self.pending_releases.clear()
        self.stop_drive(msg)
        self.output.set_steering(0.0)

    def close(self):
        if self.closed:
            return
        self.emergency_stop("Closing")
        self.closed = True
        self.output.neutral_all()
        self.root.after_idle(self.root.destroy)

    def schedule_demo(self):
        """Generate the same actions as WASD presses, with hardware disabled."""
        step = max(100, round(self.args.step_seconds * 1000))
        self.root.after(150, lambda: self.press("a"))
        self.root.after(150 + step, lambda: self.release("a"))
        self.root.after(150 + step * 2, lambda: self.press("d"))
        self.root.after(150 + step * 3, lambda: self.release("d"))
        self.root.after(150 + step * 4, lambda: self.press("w"))
        self.root.after(150 + step * 10, lambda: self.release("w"))
        self.root.after(150 + step * 11, self.close)


class _SelfTestRoot:
    """Small deterministic replacement for Tk's callback scheduler."""

    def __init__(self):
        self.callbacks = []
        self.next_id = 0

    def after(self, _milliseconds, callback):
        self.next_id += 1
        self.callbacks.append((self.next_id, callback))
        return self.next_id

    def after_cancel(self, callback_id):
        self.callbacks = [item for item in self.callbacks if item[0] != callback_id]

    def after_idle(self, callback):
        return self.after(0, callback)

    def run_next(self):
        if not self.callbacks:
            raise AssertionError("expected a scheduled callback")
        _, callback = self.callbacks.pop(0)
        callback()


class _SelfTestController(Controller):
    def build_ui(self):
        self.messages = []

    def set_status(self, msg):
        self.messages.append(msg)


def run_self_test(args):
    """Exercise steering, key-release handling, acceleration, and fail-safe stops."""
    args.dry_run = True
    args.demo = False
    args.no_arm = True
    args.mode = "steady"
    root = _SelfTestRoot()
    ctl = _SelfTestController(root, args)

    class Event:
        def __init__(self, key):
            self.keysym = key

    ctl.on_key_press(Event("a"))
    assert ctl.output.steering == -args.steering_amount
    ctl.on_key_release(Event("a"))
    root.run_next()
    assert ctl.output.steering == 0.0

    ctl.on_key_press(Event("d"))
    assert ctl.output.steering == args.steering_amount
    ctl.on_key_press(Event("a"))
    assert ctl.output.steering == 0.0
    ctl.release("a")
    assert ctl.output.steering == args.steering_amount
    ctl.release("d")
    assert ctl.output.steering == 0.0

    ctl.on_key_press(Event("w"))
    assert ctl.state == "driving"
    assert ctl.output.esc_motor_throttle == args.throttle
    ctl.on_key_release(Event("w"))
    root.run_next()
    assert ctl.state == "idle" and ctl.output.esc_motor_throttle == 0.0

    ctl.args.mode = "verified"
    ctl.press("w")
    assert ctl.output.esc_motor_throttle == ESC_SEQUENCE[0]
    for expected in ESC_SEQUENCE[1:]:
        root.run_next()
        assert ctl.output.esc_motor_throttle == expected
    root.run_next()
    assert ctl.output.esc_motor_throttle == ESC_SEQUENCE[0]
    ctl.release("w")
    assert ctl.output.esc_motor_throttle == 0.0

    ctl.args.mode = "steady"
    ctl.armed = False
    ctl.press("w")
    assert ctl.state == "arming" and ctl.output.esc_motor_throttle == ESC_SEQUENCE[0]
    for expected in ESC_SEQUENCE[1:]:
        root.run_next()
        assert ctl.output.esc_motor_throttle == expected
    root.run_next()
    assert ctl.state == "settling" and ctl.output.esc_motor_throttle == 0.0
    root.run_next()
    assert ctl.state == "driving" and ctl.output.esc_motor_throttle == args.throttle

    ctl.press("d")
    ctl.on_key_press(Event("s"))
    assert ctl.state == "idle"
    assert ctl.output.steering == 0.0 and ctl.output.esc_motor_throttle == 0.0
    print("SELF-TEST PASS: A/D steering, verified W cycles, steady mode, S stop, and emergency neutral")


def main():
    args = parse_args()
    if args.self_test:
        run_self_test(args)
        return

    import tkinter as tk

    root = tk.Tk()
    ctl = Controller(root, args)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: root.after_idle(ctl.close))
    try:
        root.mainloop()
    finally:
        ctl.output.neutral_all()


if __name__ == "__main__":
    main()
