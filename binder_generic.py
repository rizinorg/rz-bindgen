from clang.wrapper import CursorKind

from header import Header
from writer import BufferedWriter, DirectWriter
from binder import rizin


class BinderGeneric:
    name: str

    def __init__(self, header: Header, name: str):
        rizin.headers.add(header)
        rizin.generics.append(self)

        struct = header.typedefs[name].underlying_typedef_type.get_declaration()
        assert struct.kind == CursorKind.STRUCT_DECL
        rizin.generic_names[struct.spelling] = name

        self.name = name

    def merge(self, writer: DirectWriter):
        writer.line(f"%define %{self.name}(TYPE)")
        with writer.indent():
            writer.line("%{")
            writer.line(f"typedef {self.name} {self.name}_##TYPE;")
            writer.line("%}")
            writer.line(f"typedef struct {{}} {self.name}_##TYPE;")
        writer.line("%enddef")
