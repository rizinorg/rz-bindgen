from typing import Optional, TextIO
from enum import Enum

from clang.wrapper import CursorKind, Func, Struct

from binder import rizin
from writer import BufferedWriter, DirectWriter


class FuncKind(Enum):
    CONSTRUCTOR = 0
    DESTRUCTOR = 1
    THIS = 2
    STATIC = 3


class BinderFunc:
    writer: BufferedWriter

    def __init__(self, func: Func, kind: FuncKind, *, name: Optional[str] = None):
        writer = BufferedWriter()
        self.writer = writer

        # Args
        args_outer = []
        args_inner = []
        for arg in func.get_arguments():
            assert arg.kind == CursorKind.PARM_DECL
            args_inner.append(arg.spelling)
            args_outer.append(rizin.stringify_decl(arg, arg.type))

        if kind == FuncKind.CONSTRUCTOR:
            args_inner_str = ", ".join(args_inner)
            args_outer_str = ", ".join(args_outer)
            writer.line(f"{name}({args_outer_str}) {{")
        elif kind == FuncKind.DESTRUCTOR:
            args_outer_str = ", ".join(args_outer[1:])
            args_inner_str = ", ".join(["$self"] + args_inner[1:])
            writer.line(f"~{name}({args_outer_str}) {{")
        elif kind == FuncKind.THIS:
            args_outer_str = ", ".join(args_outer[1:])
            args_inner_str = ", ".join(["$self"] + args_inner[1:])
            decl = rizin.stringify_decl(func, func.result_type, name=name)
            writer.line(f"{decl}({args_outer_str}) {{")
        elif kind == FuncKind.STATIC:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(args_inner)
            decl = rizin.stringify_decl(func, func.result_type, name=name)
            writer.line(f"static {decl}({args_outer_str}) {{")

        with writer.indent():
            writer.line(f"return {func.spelling}({args_inner_str});")
        writer.line("}")

    def write(self, writer: DirectWriter) -> None:
        writer.merge(self.writer)
