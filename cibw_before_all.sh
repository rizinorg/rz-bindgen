# SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
# SPDX-License-Identifier: LGPL-3.0-only

set -ex

# Install deps
pip3 install meson ninja meson-python build

if command -v apt; then
    set +e
    grep VERSION_CODENAME=stretch /etc/os-release >/dev/null 2>/dev/null
    if [[ $? == 0 ]] ; then
	# Required because manylinux_2_24 uses Debian Stretch and the repos are not available anymore
        echo "deb http://archive.debian.org/debian stretch main" > /etc/apt/sources.list
        echo "deb http://archive.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list
        echo "Acquire::Check-Valid-Until no;" > /etc/apt/apt.conf.d/99no-check-valid-until
    fi
    set -e
    apt update && apt install --assume-yes libclang-7-dev clang-7 llvm-7
elif command -v apk; then
    apk update && apk add clang-dev
elif command -v yum; then
    yum -y install centos-release-scl llvm-toolset-7.0 llvm-toolset-7.0-llvm-devel
    source scl_source enable llvm-toolset-7.0 || true
fi

pushd rizin

if [[ "$OSTYPE" =~ msys* ]]; then
    meson setup --buildtype=release --prefix='c:/rizin' --vsenv build
else
    meson setup --buildtype=release --libdir=lib build
fi

meson install -C build
popd

if command -v apt; then
    if [ ! -e dist/*.tar.gz ] ; then
        python3 -m build --sdist
    fi
fi
