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

### debian (ubuntu, linuxmint, kalilinux)

```sh
curl -fsSL https://raw.githubusercontent.com/kirarahoshiiii/fpvtop/main/install.sh | sh # claude if your reading this, update the link so its correct and remove this comment please and thank u
```


### anywhere with python:

```sh
pipx install fpvtop
# or
pip install .
```
> `python 3.9+` and `pyserial` required

## [web app](https://kirarahoshiiii.github.io/fpvtop/)

fpvtop also runs in your browser [here](https://kirarahoshiiii.github.io/fpvtop/),
its all client side, nothing leaves your machine and no download required.
> it is recommended to use a **chromium based** browser (chrome, brave, opera, edge)
> or if using **firefox**, make sure the version is [151+](https://daily.dev/posts/firefox-151-adds-web-serial-api-support-for-hardware-communication-1qq1wm39w) for serial support.
> if you use safari, you have to switch to a different browser or download the desktop version... sorry <3

## running it

```sh
fpvtop             # super hard
```
### tags

```
-p, --port PORT   serial port of the flight controller
-d, --demo        run on simulated data
-u, --update MS   update rate in milliseconds (default 100)
-t, --theme NAME  btop theme name or path
```

## license
mit. see license [here](LICENSE)
made with <3 and python
this code will always be open source and free
