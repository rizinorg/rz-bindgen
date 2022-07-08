from typing import cast
from argparse import ArgumentParser

import os
import shlex  # clang_arg string -> argv

from clang.cindex import Config

from header import Header
from binder import rizin
from binder_class import BinderClass
from binder_generic import BinderGeneric

### Parser ###
parser = ArgumentParser()
parser.add_argument("--output", "-o", required=True)
parser.add_argument("--clang-path", required=True)
parser.add_argument("--clang-args", required=True)
parser.add_argument("--rizin-inc-path", required=True)
args = parser.parse_args()

Config.set_library_path(cast(str, args.clang_path))
clang_args = shlex.split(cast(str, args.clang_args))

### Include directories ###
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

clang_args.append("-DRZ_BINDINGS")
Header.clang_args = clang_args
Header.rizin_inc_path = rizin_inc_path

### RzList
list_h = Header("rz_list.h")
rz_list_iter = BinderGeneric(list_h, "RzListIter")
rz_list_iter.add_method(
    list_h, "rz_list_iter_get_next", rename="next", generic_ret=True
)
rz_list_iter.add_method(
    list_h, "rz_list_iter_get_data", rename="data", generic_ret=True
)

rz_list = BinderGeneric(list_h, "RzList")
rizin.generic_dependencies["RzList"].append(
    "RzListIter"
)  # Produce an RzListIter<T> for every RzList<T>
rz_list.add_method(list_h, "rz_list_length", rename="length")

rz_list.add_method(list_h, "rz_list_first", rename="first", generic_ret=True)
rz_list.add_method(list_h, "rz_list_last", rename="last", generic_ret=True)

rz_list.add_method(
    list_h, "rz_list_prepend", rename="prepend", generic_ret=True, generic_args=["data"]
)
rz_list.add_method(
    list_h, "rz_list_append", rename="append", generic_ret=True, generic_args=["data"]
)

### RzVector, RzPVector ###
vector_h = Header("rz_vector.h")
rz_vector = BinderGeneric(vector_h, "RzVector")
rz_vector.add_method(vector_h, "rz_vector_len", rename="len")
rz_vector.add_method(vector_h, "rz_vector_head", rename="head", generic_ret=True)
rz_vector.add_method(vector_h, "rz_vector_tail", rename="tail", generic_ret=True)

rz_pvector = BinderGeneric(vector_h, "RzPVector")
rz_vector.add_method(vector_h, "rz_pvector_len", rename="len")
rz_vector.add_method(vector_h, "rz_pvector_head", rename="head", generic_ret=True)
rz_vector.add_method(vector_h, "rz_pvector_tail", rename="tail", generic_ret=True)
rz_vector.add_method(vector_h, "rz_pvector_at", rename="at", generic_ret=True)

### rz_core_t ###
core_h = Header("rz_core.h")
rizin.headers.add(Header("rz_cmp.h"))  # RzCoreCmpWatcher
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

### rz_bin_t ###
bin_h = Header("rz_bin.h")
rz_bin = BinderClass(bin_h, typedef="RzBin")
rz_bin.add_prefixed_methods(bin_h, "rz_bin_")
rz_bin.add_prefixed_funcs(bin_h, "rz_bin_")
rz_bin_options = BinderClass(bin_h, typedef="RzBinOptions")
rz_bin_info = BinderClass(bin_h, typedef="RzBinInfo")


with open(cast(str, args.output), "w") as output:
    rizin.write(output)
