# SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
# SPDX-License-Identifier: LGPL-3.0-only

set -ex

# Install deps
pip3 install meson ninja meson-python build

if command -v apt; then
    apt update && apt install --assume-yes libclang-dev clang llvm
elif command -v apk; then
    apk update && apk add clang-dev
elif command -v yum; then
    yum install -y clang llvm clang-devel
fi

pushd rizin

if [[ "$OSTYPE" =~ msys* ]]; then
    meson setup --buildtype=release --prefix='c:/rizin' --vsenv build
else
    meson setup --buildtype=release --libdir=lib build
fi

meson install -C build
popd

if [ ! -e dist/*.tar.gz ] ; then
    python3 -m build --sdist
fi
