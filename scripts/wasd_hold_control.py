#!/usr/bin/env python3
"""True key-down/key-up WASD control for the AGX Orin JetRacer.

Unlike a terminal, Tk receives key press and release events and can track W+D
at the same time.  Holding W repeats the exact four-step VXL-3s burst that was
verified on this car.  Releasing W immediately returns the ESC to neutral.

Run from the Jetson desktop with all driven wheels off the ground:
    ~/jr/bin/python ~/JetRacer-JetPack7/scripts/wasd_hold_control.py
"""

import argparse
import signal
import tkinter as tk

from wasd_control import CarOutput, ESC_SEQUENCE


RELEASE_DEBOUNCE_MS = 80


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steering-channel", type=int, default=1)
    parser.add_argument("--esc-channel", type=int, default=2)
    parser.add_argument("--steering-amount", type=float, default=0.3)
    parser.add_argument(
        "--step-seconds",
        type=float,
        default=1.0,
        help="duration of each verified ESC pulse; 1.0 is the tested value",
    )
    parser.add_argument("--cycle-gap-seconds", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true", help="disable hardware output")
    parser.add_argument("--demo", action="store_true", help="automated GUI exercise; requires --dry-run")
    args = parser.parse_args()

    if args.steering_channel == args.esc_channel:
        parser.error("steering and ESC channels must be different")
    if not 0 <= args.steering_channel <= 15 or not 0 <= args.esc_channel <= 15:
        parser.error("PCA9685 channels must be between 0 and 15")
    if not 0 < args.steering_amount <= 1:
        parser.error("--steering-amount must be between 0 and 1")
    if args.step_seconds <= 0 or args.cycle_gap_seconds < 0:
        parser.error("timing values must be non-negative and step duration must be positive")
    if args.demo and not args.dry_run:
        parser.error("--demo is only available with --dry-run")
    return args


class WasdHoldController:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.output = CarOutput(args.steering_channel, args.esc_channel, args.dry_run)
        self.pressed = set()
        self.pending_releases = {}
        self.drive_after = None
        self.sequence_index = None
        self.cycles = 0
        self.closed = False

        root.title("JetRacer WASD Control")
        root.geometry("700x360")
        root.configure(bg="#151a20")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind_all("<KeyPress>", self.on_key_press)
        root.bind_all("<KeyRelease>", self.on_key_release)
        root.bind("<FocusOut>", self.on_focus_out)

        title = tk.Label(
            root,
            text="JetRacer WASD Control",
            font=("Sans", 24, "bold"),
            fg="#76b900",
            bg="#151a20",
        )
        title.pack(pady=(22, 8))

        instructions = (
            "Hold W: continuous verified bursts    Hold A / D: steer\n"
            "S or Space: immediate stop    C: centre    Q / Esc: safe exit"
        )
        tk.Label(root, text=instructions, font=("Sans", 15), fg="white", bg="#151a20").pack(pady=8)

        self.status_var = tk.StringVar(value="Click this window, then hold W. Wheels must be off the ground.")
        tk.Label(
            root,
            textvariable=self.status_var,
            font=("Monospace", 14),
            fg="#f0c674",
            bg="#151a20",
            wraplength=650,
            justify="center",
        ).pack(pady=25)

        self.detail_var = tk.StringVar()
        tk.Label(
            root,
            textvariable=self.detail_var,
            font=("Monospace", 12),
            fg="#c5c8c6",
            bg="#151a20",
        ).pack(pady=5)

        tk.Label(
            root,
            text="Focus loss is an emergency stop. The ESC is neutral on exit.",
            font=("Sans", 11),
            fg="#cc6666",
            bg="#151a20",
        ).pack(side="bottom", pady=20)

        self.update_details()
        root.after(100, root.focus_force)
        # Keep Python callbacks flowing even while the GUI is idle so SIGINT,
        # SIGTERM, and SIGHUP handlers are dispatched promptly.
        root.after(100, self.signal_heartbeat)

        if args.demo:
            self.schedule_demo()

    def signal_heartbeat(self):
        if not self.closed:
            self.root.after(100, self.signal_heartbeat)

    def set_status(self, message):
        self.status_var.set(message)
        self.update_details()
        if self.args.dry_run:
            print(message, flush=True)

    def update_details(self):
        driving = self.sequence_index is not None
        self.detail_var.set(
            f"steering={self.output.steering:+.2f} ch{self.output.steering_channel}    "
            f"ESC={self.output.pulse_us(self.output.esc_channel)} us ch{self.output.esc_channel}    "
            f"burst={'ACTIVE' if driving else 'neutral'}    cycles={self.cycles}"
        )

    def on_key_press(self, event):
        key = event.keysym.lower()
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            self.root.after_cancel(pending)
        if key in self.pressed:
            return
        self.press(key)

    def on_key_release(self, event):
        key = event.keysym.lower()
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            self.root.after_cancel(pending)
        self.pending_releases[key] = self.root.after(
            RELEASE_DEBOUNCE_MS,
            lambda key=key: self.release(key),
        )

    def press(self, key):
        self.pressed.add(key)
        if key == "w":
            if self.sequence_index is None:
                self.start_burst()
        elif key in ("a", "d"):
            self.apply_steering()
        elif key in ("s", "space"):
            self.emergency_stop("STOP pressed")
        elif key == "c":
            self.pressed.discard("a")
            self.pressed.discard("d")
            self.apply_steering()
            self.set_status("Steering centred")
        elif key in ("q", "escape"):
            self.close()

    def release(self, key):
        self.pending_releases.pop(key, None)
        self.pressed.discard(key)
        if key == "w":
            self.stop_drive("W released: ESC neutral")
        elif key in ("a", "d"):
            self.apply_steering()

    def apply_steering(self):
        left = "a" in self.pressed
        right = "d" in self.pressed
        if left == right:
            value = 0.0
        else:
            value = -self.args.steering_amount if left else self.args.steering_amount
        self.output.set_steering(value)
        self.set_status("Steering left" if value < 0 else "Steering right" if value > 0 else "Steering centred")

    def start_burst(self):
        if "w" not in self.pressed or self.closed:
            return

        # A fresh NvidiaRacecar/ServoKit instance before every cycle is part of
        # the physically verified behavior on this VXL-3s installation.
        self.output.reinitialize()
        self.apply_steering()
        self.sequence_index = 0
        self.output.set_esc_motor_throttle(ESC_SEQUENCE[0])
        self.set_status(f"W held: burst step 1/4 ({self.output.pulse_us(self.output.esc_channel)} us)")
        self.drive_after = self.root.after(round(self.args.step_seconds * 1000), self.advance_burst)

    def advance_burst(self):
        self.drive_after = None
        if "w" not in self.pressed or self.closed:
            self.stop_drive("W released: ESC neutral")
            return

        if self.sequence_index < len(ESC_SEQUENCE) - 1:
            self.sequence_index += 1
            self.output.set_esc_motor_throttle(ESC_SEQUENCE[self.sequence_index])
            self.set_status(
                f"W held: burst step {self.sequence_index + 1}/4 "
                f"({self.output.pulse_us(self.output.esc_channel)} us)"
            )
            self.drive_after = self.root.after(round(self.args.step_seconds * 1000), self.advance_burst)
            return

        self.cycles += 1
        self.output.neutral_esc()
        self.sequence_index = None
        self.set_status(f"Burst {self.cycles} complete; repeating while W is held")
        self.drive_after = self.root.after(round(self.args.cycle_gap_seconds * 1000), self.start_burst)

    def stop_drive(self, message):
        if self.drive_after is not None:
            self.root.after_cancel(self.drive_after)
            self.drive_after = None
        self.sequence_index = None
        self.output.neutral_esc()
        self.set_status(message)

    def emergency_stop(self, message):
        self.pressed.clear()
        for callback in self.pending_releases.values():
            self.root.after_cancel(callback)
        self.pending_releases.clear()
        self.stop_drive(message)
        self.output.set_steering(0.0)
        self.update_details()

    def on_focus_out(self, _event):
        if not self.closed:
            self.emergency_stop("Window focus lost: ALL STOP")

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.emergency_stop("Closing: ALL STOP")
        self.output.neutral_all()
        self.root.after_idle(self.root.destroy)

    def schedule_demo(self):
        step_ms = max(1, round(self.args.step_seconds * 1000))
        self.root.after(150, lambda: self.press("w"))
        self.root.after(150 + step_ms, lambda: self.press("d"))
        self.root.after(150 + step_ms * 5, lambda: self.release("d"))
        self.root.after(150 + step_ms * 9, lambda: self.release("w"))
        self.root.after(150 + step_ms * 10, self.close)


def main():
    args = parse_args()
    root = tk.Tk()
    controller = WasdHoldController(root, args)

    def stop_on_signal(_signum, _frame):
        root.after_idle(controller.close)

    signal.signal(signal.SIGINT, stop_on_signal)
    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGHUP, stop_on_signal)

    try:
        root.mainloop()
    finally:
        controller.output.neutral_all()


if __name__ == "__main__":
    main()
