from typing import List, Set, Optional
from enum import Enum

from clang.wrapper import CursorKind, Func

from binder import rizin
from writer import BufferedWriter, DirectWriter


class FuncKind(Enum):
    CONSTRUCTOR = 0
    DESTRUCTOR = 1
    THIS = 2
    STATIC = 3


class BinderFunc:
    writer: BufferedWriter

    def __init__(
        self,
        func: Func,
        kind: FuncKind,
        *,
        name: Optional[str] = None,
        generic_ret: bool = False,
        generic_args: Optional[List[str]] = None,
    ):
        writer = BufferedWriter()
        self.writer = writer

        ### Args ###
        args_outer = []
        args_inner = []

        # Ignore first argument for certain types
        args = func.get_arguments()
        if kind in [FuncKind.DESTRUCTOR, FuncKind.THIS]:
            next(args)

        if generic_args is None:
            generic_args = []

        for arg in args:
            assert arg.kind == CursorKind.PARM_DECL
            args_inner.append(arg.spelling)
            args_outer.append(
                rizin.stringify_decl(
                    arg, arg.type, generic=(arg.spelling in generic_args)
                )
            )

        for generic_arg in generic_args:
            assert generic_arg in args_inner, "nonexistent generic argument specified"

        ### Attrs ###
        attrs = BinderFunc.get_function_attrs(func)

        if kind == FuncKind.CONSTRUCTOR:
            args_inner_str = ", ".join(args_inner)
            args_outer_str = ", ".join(args_outer)
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
            if "RZ_DEPRECATE" in attrs:
                writer.line("if (rizin_warn_deprecate) {")
                with writer.indent():
                    writer.line(
                        f"""puts("Warning: `{name}` calls deprecated function `{func.spelling}`");"""
                    )
                writer.line("}")
            writer.line(f"return {func.spelling}({args_inner_str});")
        writer.line("}")

    @staticmethod
    def get_function_attrs(func: Func) -> Set[str]:
        if hasattr(func, "attrs"):
            return func.attrs

        attrs = set()
        for child in func.get_children():
            if child.kind != CursorKind.ANNOTATE_ATTR:
                continue
            attrs.add(child.spelling)
            func.attrs = attrs
        return attrs

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.writer)
