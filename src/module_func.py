"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Dict, Optional
from enum import Enum

from clang.wrapper import CursorKind, Func

from module import rizin
from module_typemap import ModuleTypemap
from writer import BufferedWriter, DirectWriter


class FuncKind(Enum):
    CONSTRUCTOR = 0
    DESTRUCTOR = 1
    THIS = 2
    STATIC = 3


class ModuleFunc:
    writer: BufferedWriter
    contract: BufferedWriter
    typemaps: List[ModuleTypemap]

    def __init__(
        self,
        func: Func,
        kind: FuncKind,
        *,
        name: Optional[str] = None,
        generic_ret: bool = False,
        generic_args: Optional[List[str]] = None,
        default_args: Optional[Dict[str, str]] = None,
        typemaps: Optional[List[ModuleTypemap]] = None,
    ):
        writer = BufferedWriter()
        self.writer = writer

        ### Typemaps ###
        self.typemaps = typemaps or []
        for typemap in self.typemaps:
            typemap.check(func)

        ### Args ###
        # Ignore first argument for certain types
        args = list(func.get_arguments())
        if kind in [FuncKind.DESTRUCTOR, FuncKind.THIS]:
            args = args[1:]

        # Process generics/defaults
        if generic_args is None:
            generic_args = []
        if default_args is None:
            default_args = {}

        args_outer = []
        args_inner = []
        for arg in args:
            assert arg.kind == CursorKind.PARM_DECL
            if arg.spelling == "self":
                # Rename self to _self to avoid conflict with SWIG
                args_inner.append("_self")
                args_outer.append(
                    rizin.stringify_decl(
                        arg,
                        arg.type,
                        generic=(arg.spelling in generic_args),
                        name="_self",
                    )
                )
            else:
                args_inner.append(arg.spelling)
                arg_outer = rizin.stringify_decl(
                    arg, arg.type, generic=(arg.spelling in generic_args)
                )
                if arg.spelling in default_args:
                    arg_outer += f" = {default_args[arg.spelling]}"
                args_outer.append(arg_outer)

        # Sanity check
        for generic_arg in generic_args:
            assert generic_arg in args_inner, "nonexistent generic argument specified"
        for default_arg in default_args.keys():
            assert default_arg in args_inner, "nonexistent default argument specified"

        if kind == FuncKind.CONSTRUCTOR:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(args_inner)
            writer.line(f"{name}({args_outer_str}) {{")
        elif kind == FuncKind.DESTRUCTOR:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(["$self"] + args_inner)
            writer.line(f"~{name}({args_outer_str}) {{")
        elif kind == FuncKind.THIS:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(["$self"] + args_inner)
            decl = rizin.stringify_decl(
                func, func.result_type, name=name, generic=generic_ret
            )
            writer.line(f"{decl}({args_outer_str}) {{")
        elif kind == FuncKind.STATIC:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(args_inner)
            decl = rizin.stringify_decl(
                func, func.result_type, name=name, generic=generic_ret
            )
            writer.line(f"static {decl}({args_outer_str}) {{")

        with writer.indent():
            if "RZ_DEPRECATE" in func.attrs:
                writer.line(f'rizin_try_warn_deprecate("{name}", "{func.spelling}");')
            writer.line(f"return {func.spelling}({args_inner_str});")
        writer.line("}")

        ### Contracts ###
        contract = BufferedWriter()
        self.contract = contract

        args_nonnull = []

        for arg in args:
            if "RZ_NONNULL" in arg.attrs:
                args_nonnull.append(arg.spelling)

        if args_nonnull:
            contract.line(f"%contract {name}({args_outer_str}) {{", "require:")
            with contract.indent():
                for contract_arg in args_nonnull:
                    contract.line(f"{contract_arg} != NULL;")
            contract.line("}")

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.contract)

        for typemap in self.typemaps:
            typemap.merge_activate(writer)

        writer.merge(self.writer)

        for typemap in self.typemaps:
            typemap.merge_deactivate(writer)
