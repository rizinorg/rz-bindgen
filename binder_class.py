from typing import List, Set, Optional, TextIO

from clang.wrapper import (
    CursorKind,
    Struct,
    StructField,
    StructUnionField,
    Func,
    TypeKind,
)

from header import Header
from writer import BufferedWriter, DirectWriter
from binder import rizin
from binder_func import BinderFunc, FuncKind


def get_function_attrs(func: Func) -> Set[str]:
    attrs = set()
    for child in func.get_children():
        if child.kind != CursorKind.ANNOTATE_ATTR:
            continue
        attrs.add(child.spelling)
    return attrs


class BinderClass:
    struct: Struct
    struct_writer: BufferedWriter
    funcs: List[BinderFunc]

    def __init__(
        self,
        header: Header,
        *,
        typedef: Optional[str] = None,
        struct: Optional[str] = None,
        rename: Optional[str] = None,
    ):
        rizin.headers.add(header)
        rizin.classes.append(self)

        # Get STRUCT_DECL cursor
        if typedef:
            assert not struct, "specify typedef or struct, not both"
            typedef_cursor = header.typedefs[typedef]
            struct_cursor = typedef_cursor.underlying_typedef_type.get_declaration()
            assert struct_cursor.kind == CursorKind.STRUCT_DECL
            rename = rename or typedef_cursor.spelling
        elif struct:
            struct_cursor = header.structs[struct]
        else:
            raise Exception("specify either typedef or struct")

        self.struct = struct_cursor
        self.struct_writer = BufferedWriter()
        self.funcs = []

        self.gen_struct(struct_cursor)
        if rename:
            self.struct_writer.line(
                f"typedef struct {struct_cursor.spelling} {rename};"
            )

    def add_constructor(self, header: Header, name: str) -> None:
        rizin.headers.add(header)
        func = BinderFunc(
            header.funcs[name], FuncKind.CONSTRUCTOR, name=self.struct.spelling
        )
        self.funcs.append(func)

    def add_destructor(self, header: Header, name: str) -> None:
        rizin.headers.add(header)
        func = BinderFunc(
            header.funcs[name], FuncKind.DESTRUCTOR, name=self.struct.spelling
        )
        self.funcs.append(func)

    def add_prefixed_methods(self, header: Header, prefix: str) -> None:
        rizin.headers.add(header)

        def predicate(func: Func) -> bool:
            if func.spelling in header.used:
                return False  # not used
            if not func.spelling.startswith(prefix):
                return False  # correct prefix
            if "RZ_API" not in get_function_attrs(func):
                return False  # RZ_API

            args = list(func.get_arguments())
            if len(args) == 0:
                return False

            arg = args[0]
            assert arg.kind == CursorKind.PARM_DECL

            if arg.type.kind != TypeKind.POINTER:
                return False
            return (
                arg.type.get_pointee().get_canonical().get_declaration() == self.struct
            )

        for func in filter(predicate, header.funcs.values()):
            header.used.add(func.spelling)
            binderfunc = BinderFunc(
                func, FuncKind.THIS, name=func.spelling[len(prefix) :]
            )
            self.funcs.append(binderfunc)

    def add_prefixed_funcs(self, header: Header, prefix: str) -> None:
        rizin.headers.add(header)

        def predicate(func: Func) -> bool:
            if func.spelling in header.used:
                return False  # not used
            if not func.spelling.startswith(prefix):
                return False  # correct prefix
            if "RZ_API" not in get_function_attrs(func):
                return False  # RZ_API
            return True

        for func in filter(predicate, header.funcs.values()):
            header.used.add(func.spelling)
            binderfunc = BinderFunc(
                func, FuncKind.STATIC, name=func.spelling[len(prefix) :]
            )
            self.funcs.append(binderfunc)

    def gen_struct(self, struct: Struct) -> None:
        def gen_field(field: StructField) -> None:
            decl = rizin.stringify_decl(field, field.type)
            self.struct_writer.line(f"{decl};")

        def gen_union(field: StructUnionField) -> None:
            self.struct_writer.line("union {")
            with self.struct_writer.indent():
                for union_field in field.get_children():
                    assert union_field.kind == CursorKind.FIELD_DECL
                    gen_field(union_field)
            self.struct_writer.line("}")

        self.struct_writer.line(f"struct {struct.spelling} {{")
        with self.struct_writer.indent():
            for field in struct.get_children():
                if field.kind == CursorKind.STRUCT_DECL:
                    self.gen_struct(field)
                elif field.kind == CursorKind.FIELD_DECL:
                    gen_field(field)
                elif field.kind == CursorKind.UNION_DECL:
                    gen_union(field)
                else:
                    raise Exception(
                        f"Unexpected struct child of kind: {field.kind} at {field.location}"
                    )
        self.struct_writer.line("};")

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.struct_writer)

        writer.line(f"%extend {self.struct.spelling} {{")
        with writer.indent():
            for func in self.funcs:
                func.write(writer)
        writer.line("}")
