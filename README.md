# [fpvtop](https://github.com/kirarahoshiiii/fpvtop/)

btop style terminal monitor for betaflight fcs over msp

this is **not** a fork of [btop](https://github.com/aristocratos/btop)

![demo](assets/demo.gif)

> recorded automatically with [vhs](https://github.com/charmbracelet/vhs) on every release, straight from `fpvtop -d`

## install

### archlinux (cachyos, endeavouros, manjaro)

```sh
yay -S fpvtop
# or                            # i use arch btw
paru -S fpvtop
```

### debian (ubuntu, linuxmint, kalilinux)

```sh
curl -fsSL https://raw.githubusercontent.com/kirarahoshiiii/fpvtop/main/install.sh | sh
```

### windows

```powershell
scoop bucket add fpvtop https://github.com/kirarahoshiiii/scoop-fpvtop
scoop install fpvtop
```

or no python needed, you can run the app by downloading **`fpvtop.exe`** or **`fpvtop-cli.exe`** from the
[latest release](https://github.com/kirarahoshiiii/fpvtop/releases) double click `fpvtop.exe` to open it in windows terminal or
run `fpvtop-cli.exe` from any terminal
> **note:** upon running the `.exe` you will get a popup, this is because the `.exe` is unsigned, signing it would cost upwards of [$380 a year](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/).

or with python:

```powershell
py -m pip install fpvtop
```

> fcs show up as a com port out of the box on windows 10 and higher
> use the [windows terminal](https://aka.ms/terminal) so the glyphs render right

### macos

```sh
brew install kirarahoshiiii/fpvtop/fpvtop
```

> installs from the [tap](https://github.com/kirarahoshiiii/homebrew-fpvtop), tab completions included

### anywhere with python:

```sh
pipx install fpvtop
```
> `python 3.9+` and `pyserial` required

### compiling from source

```sh
git clone https://github.com/kirarahoshiiii/fpvtop
cd fpvtop
pip install .
```

> or skip the install and run it straight from the clone: `python -m fpvtop -d`

## [web app](https://kirarahoshiiii.github.io/fpvtop/)

fpvtop also runs in your browser [here](https://kirarahoshiiii.github.io/fpvtop/)

its all client side, nothing leaves your machine and no download required.
> it is recommended to use a **chromium based** browser (chrome, brave, opera, edge)
> or if using **firefox**, make sure the version is [151+](https://daily.dev/posts/firefox-151-adds-web-serial-api-support-for-hardware-communication-1qq1wm39w) for serial support.

> if you use safari, you have to switch to a different browser or download the desktop version... sorry <3

## running it

```sh
fpvtop             # super hard
```

### testing without hardware

`fpvtop -d` runs the whole dashboard on simulated flight data, and the test suite
includes an end to end pty sim so you can run and test it without an actual fc plugged in

```sh
./tests/run_all.sh
```


### tags

```
-p, --port PORT   serial port of the flight controller
-d, --demo        run on simulated data
-u, --update MS   update rate in milliseconds (default 100)
-t, --theme NAME  btop theme name or path
-V, --version     print the version
```

tab completion for **bash**, **zsh** and **fish** comes with the aur, deb and brew packages
(completes the tags, your serial ports and your btop themes)

pipx installs can get the completions from [`packaging/completions/`](packaging/completions/)

## license
mit. see license [here](LICENSE)

made with <3 and python

this code will always be open source and free
