"""
Specifies a generic class
"""

from typing import List, Optional

from clang.wrapper import CursorKind

from header import Header
from writer import DirectWriter
from module import rizin
from module_func import ModuleFunc, FuncKind


class ModuleGeneric:
    """
    Represents a generic class

    Implemented as a SWIG macro definition (eg. %RzList)
    Specializations are created by calling the macro with a type (eg. %RzList(int))
    """

    name: str
    funcs: List[ModuleFunc]

    def __init__(self, header: Header, name: str):
        """
        Construct a generic from a typedef
        """
        rizin.generics.append(self)

        # typedef -> struct
        struct = header.typedefs[name].underlying_typedef_type.get_declaration()
        assert struct.kind == CursorKind.STRUCT_DECL
        rizin.generic_names[struct.spelling] = name  # add to mappings

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
        header.used.add(name)

        func = ModuleFunc(
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
            # The generic and its specializations are equal in C
            # eg. RzList_int == RzList
            writer.line("%{", f"typedef {self.name} {self.name}_##TYPE;", "%}")

            # Treat them differently in SWIG only
            writer.line(f"typedef struct {{}} {self.name}_##TYPE;")

            writer.line(f"%extend {self.name}_##TYPE {{")
            with writer.indent():
                for func in self.funcs:
                    func.merge(writer)
            writer.line("}")
        writer.line("%enddef")
