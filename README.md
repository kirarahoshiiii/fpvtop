# [fpvtop](https://github.com/kirarahoshiiii/fpvtop/)

btop style terminal monitor for betaflight fcs over msp

this is **not** a fork of [btop](https://github.com/aristocratos/btop)

## install

### archlinux (cachyos, endeavouros, manjaro)

```sh
yay -S fpvtop
# or                            # i use arch btw
paru -S fpvtop
```

> the aur upload is still in transit — until it lands, this builds the exact same package:
> `git clone https://github.com/kirarahoshiiii/fpvtop && cd fpvtop/packaging/aur && makepkg -si`

### debian (ubuntu, linuxmint, kalilinux)

```sh
curl -fsSL https://raw.githubusercontent.com/kirarahoshiiii/fpvtop/main/install.sh | sh
```

### windows

```powershell
py -m pip install git+https://github.com/kirarahoshiiii/fpvtop
```

> boards show up as a COM port out of the box on windows 10+
> use [windows terminal](https://aka.ms/terminal) so the glyphs render right

### anywhere with python:

```sh
pipx install git+https://github.com/kirarahoshiiii/fpvtop
```
> `python 3.9+` and `pyserial` required
> not on pypi (yet), the git url gives you the same thing

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

`fpv-tester` includes an end to end pty sim so you can run and test it without an actual fc plugged in

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

tab completion for **bash**, **zsh** and **fish** comes with the aur and deb packages
(completes the tags, your serial ports and your btop themes) — pip/pipx installs can
grab the files from [`packaging/completions/`](packaging/completions/)

## license
mit. see license [here](LICENSE)

made with <3 and python

this code will always be open source and free
