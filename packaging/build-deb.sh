#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION="0.1.0"
PKG_NAME="halberd-bas"
BUILD_DIR="$SCRIPT_DIR/deb-build"

echo "Building ${PKG_NAME}_${VERSION}.deb..."

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/lib/halberd"
mkdir -p "$BUILD_DIR/usr/bin"

cp "$SCRIPT_DIR/deb/DEBIAN/control" "$BUILD_DIR/DEBIAN/"
cp "$SCRIPT_DIR/deb/DEBIAN/postinst" "$BUILD_DIR/DEBIAN/"
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

cp -r "$PROJECT_ROOT/halberd" "$BUILD_DIR/usr/lib/halberd/"
cp "$PROJECT_ROOT/pyproject.toml" "$BUILD_DIR/usr/lib/halberd/"

cat > "$BUILD_DIR/usr/bin/halberd" << 'WRAPPER'
#!/bin/bash
exec python3 -m halberd.cli "$@"
WRAPPER
chmod 755 "$BUILD_DIR/usr/bin/halberd"

dpkg-deb --build "$BUILD_DIR" "$SCRIPT_DIR/${PKG_NAME}_${VERSION}_all.deb"

rm -rf "$BUILD_DIR"

echo "Built: $SCRIPT_DIR/${PKG_NAME}_${VERSION}_all.deb"
echo "Install with: sudo dpkg -i ${PKG_NAME}_${VERSION}_all.deb"
