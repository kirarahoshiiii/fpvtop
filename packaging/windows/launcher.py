import os
import shutil
import subprocess
import sys


def find_cli():
    if getattr(sys, "frozen", False):
        here = os.path.dirname(sys.executable)
    else:
        here = os.path.dirname(os.path.abspath(__file__))
    for name in ("fpvtop-cli.exe", "fpvtop-cli"):
        path = os.path.join(here, name)
        if os.path.exists(path):
            return path
    return shutil.which("fpvtop-cli.exe") or shutil.which("fpvtop-cli")


def main():
    cli = find_cli()
    if not cli:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "fpvtop-cli.exe was not found.\nKeep fpvtop.exe and fpvtop-cli.exe in the same folder.",
            "fpvtop",
            0x10,
        )
        return 1
    wt = shutil.which("wt")
    if wt:
        subprocess.Popen([wt, cli])
    else:
        subprocess.Popen(["cmd", "/c", "start", "fpvtop", cli])
    return 0


if __name__ == "__main__":
    sys.exit(main())
