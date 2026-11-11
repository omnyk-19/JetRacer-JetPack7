"""Manual control test for JetRacer on JetPack 7.

This AGX Orin car uses PCA9685 ch1 for steering and ch2 for the ESC.

Run on the Jetson with the wheels OFF the ground:
    ~/jr/bin/python manual_control_test.py center
    ~/jr/bin/python manual_control_test.py left
    ~/jr/bin/python manual_control_test.py right
    ~/jr/bin/python manual_control_test.py steering --seconds 15
    ~/jr/bin/python manual_control_test.py throttle
    ~/jr/bin/python manual_control_test.py esc-sequence

The PCA9685 keeps sending the last pulse after the script exits, so `left`/`right`/`center` hold their position.
"""
import argparse
import time

from jetracer.nvidia_racecar import NvidiaRacecar


def pulse_us(car, channel):
    pca = car.kit._pca
    return round(pca.channels[channel].duty_cycle / 65535 * 1e6 / pca.frequency)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("test", choices=["center", "left", "right", "steering", "throttle", "esc-sequence"])
    parser.add_argument("--seconds", type=float, default=15.0, help="length of the steering sweep")
    parser.add_argument("--amount", type=float, default=0.7, help="steering sweep amplitude, 0-1")
    parser.add_argument("--throttle-amount", type=float, default=0.2, help="motor test command, -1 to 1")
    parser.add_argument("--throttle-seconds", type=float, default=1.0, help="motor test command duration")
    parser.add_argument("--steering-channel", type=int, default=1, help="PCA9685 steering channel")
    parser.add_argument("--esc-channel", type=int, default=2, help="PCA9685 ESC channel")
    args = parser.parse_args()

    if args.steering_channel == args.esc_channel:
        parser.error("steering and ESC channels must be different")
    if not -1.0 <= args.throttle_amount <= 1.0:
        parser.error("--throttle-amount must be between -1 and 1")
    if args.throttle_seconds <= 0:
        parser.error("--throttle-seconds must be positive")

    car = NvidiaRacecar(
        steering_channel=args.steering_channel,
        throttle_channel=args.esc_channel,
    )  # patched: sends center steering + neutral throttle at startup
    print(
        f"start: steering ch{args.steering_channel} {pulse_us(car, args.steering_channel)} us, "
        f"ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us"
    )

    if args.test == "center":
        return
    if args.test in ("left", "right"):
        car.steering = -1.0 if args.test == "left" else 1.0
        print(
            f"holding steering {car.steering:+.1f} -> "
            f"ch{args.steering_channel} {pulse_us(car, args.steering_channel)} us"
        )
        return

    try:
        if args.test == "steering":
            t0, n = time.time(), 0
            while time.time() - t0 < args.seconds:
                car.steering = -args.amount if n % 2 == 0 else args.amount
                n += 1
                time.sleep(1.0)
            print(f"{n} swings in {time.time() - t0:.1f}s")
        elif args.test == "esc-sequence":
            # Reproduce the only waveform the Traxxas VXL-3s acknowledged during
            # initial bring-up: 1645/1352 us twice, then neutral.  The values
            # below account for throttle_gain so the continuous-servo output is
            # the same +/-0.195 used by the successful channel-2 test.
            print("Traxxas diagnostic sequence on ESC channel")
            for motor_throttle in (0.195, -0.195, 0.195, -0.195):
                car.throttle = motor_throttle / car.throttle_gain
                print(
                    f"ESC motor throttle {motor_throttle:+.3f} -> ch{args.esc_channel} "
                    f"{pulse_us(car, args.esc_channel)} us (1 s)"
                )
                time.sleep(1)
        else:
            print("neutral 3 s (ESC arming)")
            time.sleep(3)
            car.throttle = args.throttle_amount
            print(
                f"throttle {args.throttle_amount} -> ch{args.esc_channel} "
                f"{pulse_us(car, args.esc_channel)} us ({args.throttle_seconds:g} s)"
            )
            time.sleep(args.throttle_seconds)
    finally:
        car.throttle = 0.0
        car.steering = 0.0
        print(
            f"stopped: steering ch{args.steering_channel} {pulse_us(car, args.steering_channel)} us, "
            f"ESC ch{args.esc_channel} {pulse_us(car, args.esc_channel)} us"
        )


if __name__ == "__main__":
    main()
