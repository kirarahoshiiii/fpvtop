#!/bin/sh
set -eu

repo="kirarahoshiiii/fpvtop"
tag=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')
if [ -z "$tag" ]; then
    echo "could not find the latest fpvtop release" >&2
    exit 1
fi
ver=${tag#v}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if command -v apt-get >/dev/null 2>&1; then
    url="https://github.com/$repo/releases/download/$tag/fpvtop_${ver}-1_all.deb"
    echo "downloading fpvtop $ver ($url)"
    curl -fsSL -o "$tmp/fpvtop.deb" "$url"
    if [ "$(id -u)" = 0 ]; then
        apt-get install -y "$tmp/fpvtop.deb"
    else
        sudo apt-get install -y "$tmp/fpvtop.deb"
    fi
elif command -v pipx >/dev/null 2>&1; then
    pipx install "git+https://github.com/$repo"
elif command -v pip >/dev/null 2>&1; then
    pip install --user "git+https://github.com/$repo"
else
    echo "no apt, pipx or pip found - install python and pip first" >&2
    exit 1
fi

echo "done. run: fpvtop"
