function __fpvtop_ports
    command ls /dev 2>/dev/null | string match -r '^(ttyACM|ttyUSB|cu\.usbmodem).*' | string replace -r '^' '/dev/'
end

function __fpvtop_themes
    command ls ~/.config/btop/themes /usr/share/btop/themes 2>/dev/null | string match -r '.*\.theme$' | string replace -r '\.theme$' '' | sort -u
end

complete -c fpvtop -s p -l port -x -a "(__fpvtop_ports)" -d "serial port of the flight controller"
complete -c fpvtop -s d -l demo -d "run on simulated data"
complete -c fpvtop -s u -l update -x -a "50 100 250 500 1000 2000" -d "update rate in milliseconds"
complete -c fpvtop -s t -l theme -x -a "(__fpvtop_themes)" -d "btop theme name or path"
complete -c fpvtop -s V -l version -d "show version and exit"
complete -c fpvtop -s h -l help -d "show help and exit"
