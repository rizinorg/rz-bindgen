from typing import List, Optional

from clang.wrapper import CursorKind

from header import Header
from writer import DirectWriter
from binder import rizin
from binder_func import BinderFunc, FuncKind


class BinderGeneric:
    name: str
    funcs: List[BinderFunc]

    def __init__(self, header: Header, name: str):
        rizin.headers.add(header)
        rizin.generics.append(self)

        struct = header.typedefs[name].underlying_typedef_type.get_declaration()
        assert struct.kind == CursorKind.STRUCT_DECL
        rizin.generic_names[struct.spelling] = name

        self.name = name
        self.funcs = []

    def add_method(
        self,
        header: Header,
        name: str,
        *,
        rename: Optional[str] = None,
        generic_ret: bool = False,
        generic_args: Optional[List[str]] = None,
    ) -> None:
        rizin.headers.add(header)
        header.used.add(name)

        func = BinderFunc(
            header.funcs[name],
            FuncKind.THIS,
            name=rename,
            generic_ret=generic_ret,
            generic_args=generic_args,
        )
        self.funcs.append(func)

    def merge(self, writer: DirectWriter) -> None:
        writer.line(f"%define %{self.name}(TYPE)")
        with writer.indent():
            writer.line(
                "%{",
                f"typedef {self.name} {self.name}_##TYPE;",
                "%}",
                f"typedef struct {{}} {self.name}_##TYPE;",
            )

            writer.line(f"%extend {self.name}_##TYPE {{")
            with writer.indent():
                for func in self.funcs:
                    func.merge(writer)
            writer.line("}")
        writer.line("%enddef")
