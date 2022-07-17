"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List

from clang.wrapper import CursorKind, TypeKind

from header import Header
from module import rizin
from writer import BufferedWriter, DirectWriter


class ModuleDirector:
    struct_writer: BufferedWriter
    name: str
    funcs: BufferedWriter
    consts: BufferedWriter

    def __init__(self, header: Header, name: str):
        rizin.directors.append(self)
        self.name = name

        # typedef -> struct
        struct = header.typedefs[name].underlying_typedef_type.get_declaration()
        assert struct.kind == CursorKind.STRUCT_DECL

        writer = BufferedWriter()
        self.struct_writer = writer

        self.funcs = BufferedWriter()
        self.consts = BufferedWriter()

        writer.line(f"struct {name}Director {{")

        with writer.indent():
            for field in struct.get_children():
                assert field.kind == CursorKind.FIELD_DECL

                if field.type.kind != TypeKind.POINTER:
                    continue

                pointee = field.type.get_pointee()
                if pointee.kind != TypeKind.FUNCTIONPROTO:
                    continue

                args_outer: List[str] = []
                args_inner: List[str] = []

                for arg in field.get_children():
                    if arg.kind == CursorKind.PARM_DECL:
                        args_outer.append(rizin.stringify_decl(arg, arg.type))
                        args_inner.append(arg.spelling)
                    elif (
                        arg.kind != CursorKind.TYPE_REF
                        and arg.kind != CursorKind.ANNOTATE_ATTR
                    ):
                        raise Exception(
                            "Unexpected struct field child of kind: {arg.kind} at {arg.location}"
                        )

                args_outer_str = ", ".join(args_outer)
                args_inner_str = ", ".join(args_inner)
                decl = rizin.stringify_decl(field, pointee.get_result())

                # Director virtual funcs
                writer.line(f"virtual {decl}({args_outer_str}) {{")
                with writer.indent():
                    writer.line(
                        f"""throw Swig::DirectorPureVirtualException("{field.spelling}");"""
                    )
                writer.line("}")

                # Static func definition
                # const_name =
                static_name = f"SWIG_{name}_{field.spelling}"  # const_name + "_decl"

                static_decl = rizin.stringify_decl(
                    field, pointee.get_result(), name=static_name
                )
                self.funcs.line(f"static {static_decl}({args_outer_str}) {{")
                with self.funcs.indent():
                    self.funcs.line(
                        f"return SWIG{name}Director->{field.spelling}({args_inner_str});"
                    )
                self.funcs.line("}")

                # %constant static func declaration
                const_decl = rizin.stringify_decl(field, field.type, name=static_name)
                self.consts.line(f"%constant {const_decl} = {static_name};")

            writer.line(f"{name}Director() {{}}")  # Constructor
            writer.line(f"virtual ~{name}Director() {{}}")

        writer.line("};")

    def merge(self, writer: DirectWriter) -> None:
        writer.line(f"""%feature("director") {self.name}Director;""")

        writer.line("%inline %{")
        with writer.indent():
            writer.merge(self.struct_writer)

            writer.line(
                f"static {self.name}Director *SWIG{self.name}Director = NULL;",
            )
        writer.line("%}")

        writer.line("%{")
        with writer.indent():
            writer.merge(self.funcs)
        writer.line("%}")

        writer.merge(self.consts)
