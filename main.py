from typing import cast
from argparse import ArgumentParser

import os
import shlex # clang_arg string -> argv

from clang.cindex import Config

from header import Header
from binder import rizin
from binder_class import BinderClass

parser = ArgumentParser()
parser.add_argument("--output", "-o", required=True)
parser.add_argument("--clang-path", required=True)
parser.add_argument("--clang-args", required=True)
parser.add_argument("--rizin-inc-path", required=True)
args = parser.parse_args()

Config.set_library_path(cast(str, args.clang_path))
clang_args = shlex.split(cast(str, args.clang_args))

# Populate include directories
rizin_inc_path = os.path.abspath(cast(str, args.rizin_inc_path))
for segments in [
    ["."],
    ["sdb"],
    # meson project
    ["..", "..", "build"],
    ["..", "..", "subprojects", "sdb", "src"],
    ["..", "..", "build", "subprojects", "sdb"],
]:
    path = os.path.abspath(os.path.join(rizin_inc_path, *segments))
    if os.path.exists(path):
        clang_args.append(f"-I{path}")

clang_args.append(f"-DRZ_BINDINGS")
Header.clang_args = clang_args
Header.rizin_inc_path = rizin_inc_path

core_h = Header("rz_core.h")
rz_core = BinderClass(core_h, struct="rz_core_t", rename="RzCore")
rz_core.add_constructor(core_h, "rz_core_new")
rz_core.add_destructor(core_h, "rz_core_free")

# Ignore format strings
for func_name in [
    "rz_core_notify_begin",
    "rz_core_notify_done",
    "rz_core_notify_error",
    "rz_core_cmd_strf",
    "rz_core_cmdf",
    "rz_core_syscallf",
]:
    assert func_name in core_h.nodes
    core_h.used.add(func_name)

rz_core.add_prefixed_methods(core_h, "rz_core_")
rz_core.add_prefixed_funcs(core_h, "rz_core_")

# rz_core_file = rizin.Class(core_h, "RzCoreFile")


with open(cast(str, args.output), "w") as output:
    rizin.write(output)
