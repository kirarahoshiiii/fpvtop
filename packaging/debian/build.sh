#!/bin/sh
set -eu

version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$(dirname "$0")/../../fpvtop/__init__.py")
root=$(cd "$(dirname "$0")/../.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

pkgdir="$stage/fpvtop_${version}-1_all"
mkdir -p "$pkgdir/DEBIAN" \
         "$pkgdir/usr/lib/python3/dist-packages" \
         "$pkgdir/usr/bin" \
         "$pkgdir/usr/share/doc/fpvtop" \
         "$pkgdir/usr/share/bash-completion/completions" \
         "$pkgdir/usr/share/zsh/vendor-completions" \
         "$pkgdir/usr/share/fish/vendor_completions.d"

cp -r "$root/fpvtop" "$pkgdir/usr/lib/python3/dist-packages/"
rm -rf "$pkgdir/usr/lib/python3/dist-packages/fpvtop/__pycache__"
cp "$root/LICENSE" "$pkgdir/usr/share/doc/fpvtop/copyright"
cp "$root/README.md" "$pkgdir/usr/share/doc/fpvtop/"
cp "$root/packaging/completions/fpvtop.bash" "$pkgdir/usr/share/bash-completion/completions/fpvtop"
cp "$root/packaging/completions/_fpvtop" "$pkgdir/usr/share/zsh/vendor-completions/_fpvtop"
cp "$root/packaging/completions/fpvtop.fish" "$pkgdir/usr/share/fish/vendor_completions.d/fpvtop.fish"

cat > "$pkgdir/usr/bin/fpvtop" <<'EOF'
#!/usr/bin/python3
import sys
from fpvtop.main import run
sys.exit(run())
EOF
chmod 755 "$pkgdir/usr/bin/fpvtop"

size=$(du -sk "$pkgdir/usr" | cut -f1)
cat > "$pkgdir/DEBIAN/control" <<EOF
Package: fpvtop
Version: ${version}-1
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-serial
Installed-Size: ${size}
Maintainer: kirarahoshiiii <299474069+kirarahoshiiii@users.noreply.github.com>
Homepage: https://github.com/kirarahoshiiii/fpvtop
Description: btop-style live monitor for Betaflight flight controllers
 Full-screen terminal dashboard for a connected Betaflight flight
 controller over MSP: gyro rates, attitude, loop time, motor outputs
 with ESC telemetry, battery, RC link and arming state, rendered in
 btop's exact visual style.
EOF

dpkg-deb --build --root-owner-group "$pkgdir" "$root/dist/fpvtop_${version}-1_all.deb" 2>/dev/null || {
    mkdir -p "$root/dist"
    dpkg-deb --build --root-owner-group "$pkgdir" "$root/dist/fpvtop_${version}-1_all.deb"
}
echo "built dist/fpvtop_${version}-1_all.deb"
