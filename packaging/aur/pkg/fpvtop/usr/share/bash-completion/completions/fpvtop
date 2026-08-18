_fpvtop() {
    local cur prev
    cur=${COMP_WORDS[COMP_CWORD]}
    prev=${COMP_WORDS[COMP_CWORD-1]}
    case $prev in
        -p|--port)
            COMPREPLY=($(compgen -W "$(ls /dev/ttyACM* /dev/ttyUSB* /dev/cu.usbmodem* 2>/dev/null)" -- "$cur"))
            return
            ;;
        -t|--theme)
            local themes
            themes=$(command ls "$HOME/.config/btop/themes" /usr/share/btop/themes 2>/dev/null | sed -n 's/\.theme$//p' | sort -u)
            COMPREPLY=($(compgen -W "$themes" -- "$cur"))
            return
            ;;
        -u|--update)
            COMPREPLY=($(compgen -W "50 100 250 500 1000 2000" -- "$cur"))
            return
            ;;
    esac
    COMPREPLY=($(compgen -W "-p --port -d --demo -u --update -t --theme -V --version -h --help" -- "$cur"))
}
complete -F _fpvtop fpvtop
