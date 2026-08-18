# fpvtop

btop-style live terminal monitor for Betaflight flight controllers, over MSP.

Plug in a flight controller and get a full-screen, braille-graph dashboard of
what it's doing right now: gyro rates, attitude, loop time, CPU load, motor
outputs with RPM/temperature/current telemetry, battery voltage and sag,
current draw, RC link and channel activity, sensor health and arming state.

The renderer replicates btop's exact visual language — the same braille graph
symbol tables, rounded boxes with embedded border titles, block meters and
101-step color gradients — hand-rolled ANSI with no TUI library. Your btop
theme is picked up automatically from `~/.config/btop/btop.conf`, and any
btop `.theme` file works via `--theme`.

## Install

Arch (AUR):

```sh
yay -S fpvtop
```

Debian/Ubuntu — grab the `.deb` from the latest
[release](https://github.com/kirarahoshiiii/fpvtop/releases), or build it:

```sh
sh packaging/debian/build.sh
sudo apt install ./dist/fpvtop_*.deb
```

Anywhere with Python:

```sh
pipx install fpvtop        # or: pip install .
```

Python 3.9+, `pyserial` is the only dependency.

## Web app

fpvtop also runs in the browser at
**https://kirarahoshiiii.github.io/fpvtop/** — same panels, same braille
graphs, talking MSP straight to the board over Web Serial (Chrome/Edge).
It starts on simulated data; click *connect board* and pick the FC's port.
No install, nothing leaves your machine.

## Run

```sh
fpvtop
```

With no board plugged in it starts on simulated data and hot-swaps to the
real board the moment one enumerates. `q` quits, `+`/`-` change the refresh
rate.

```
-p, --port PORT   serial port of the flight controller
-d, --demo        run on simulated data
-u, --update MS   update rate in milliseconds (default 100)
-t, --theme NAME  btop theme name or path
```

## Notes

- Talks MSP v1 at 115200 baud; tested against Betaflight 4.x.
- Motor RPM/temp/current columns need ESC telemetry (DSHOT telemetry or
  `MSP_MOTOR_TELEMETRY` support); they show `-` otherwise.
- Read-only: fpvtop never writes any command that changes FC state.
