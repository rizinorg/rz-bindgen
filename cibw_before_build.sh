set -ex

# Install deps
pip install meson ninja meson-python
apt update && apt install --assume-yes libclang-7-dev clang-7 llvm-7

# Install rizin
git clone --depth 1 https://github.com/wingdeans/rizin.git -b header-types
pushd rizin

meson build && meson install -C build
popd
