"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import Optional, cast

import os
import shlex
from argparse import ArgumentParser

import cparser_header
import bindings

from clang.cindex import Config

parser = ArgumentParser()
parser.add_argument("--output-dir", "-o", required=True)
parser.add_argument("--clang-path", required=True)
parser.add_argument("--clang-args", required=True)
parser.add_argument("--rizin-include-path", required=True)
parser.add_argument("--targets", required=True)
parser.add_argument("--doxygen-path")
args = parser.parse_args()

output_dir = cast(str, args.output_dir)
Config.set_library_path(cast(str, args.clang_path))
cparser_header.clang_args = clang_args = shlex.split(cast(str, args.clang_args))
cparser_header.rizin_include_path = rizin_include_path = cast(
    str, args.rizin_include_path
)
targets = set(cast(str, args.targets).split(","))

# Add additional include directories
for segments in [
    # already isntalled `include/librz` directory
    ["."],
    ["sdb"],
    # not yet installed meson project `include` directory
    ["..", "..", "build"],
    ["..", "util", "sdb", "src"],
]:
    path = os.path.abspath(os.path.join(rizin_include_path, *segments))
    if os.path.exists(path):
        clang_args += ["-I", path]

# Enable certain annotation definitions in rz_types.h
clang_args.append("-DRZ_BINDINGS")

# Run binding specifications
bindings.run()

# Generator(s)
if "SWIG" in targets:
    import generator_swig

    generator_swig.generate(output_dir)

if "sphinx" in targets:
    import generator_sphinx

    generator_sphinx.doxygen_path = cast(Optional[str], args.doxygen_path)
    generator_sphinx.generate(output_dir)
