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

    # Used to create Python helper functions
    data_members: List[str]
    func_members: List[str]

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

        self.data_members = []
        self.func_members = []

        writer.line(f"struct {name}Director {{")

        with writer.indent():
            for field in struct.get_children():
                assert field.kind == CursorKind.FIELD_DECL

                if field.type.kind != TypeKind.POINTER:
                    self.data_members.append(field.spelling)
                    continue

                pointee = field.type.get_pointee()
                if pointee.kind != TypeKind.FUNCTIONPROTO:
                    self.data_members.append(field.spelling)
                    continue

                self.func_members.append(field.spelling)
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
                writer.line(
                    f"virtual {decl}({args_outer_str}) {{",
                    f'    throw Swig::DirectorPureVirtualException("{field.spelling}");',
                    "}",
                )

                # Static func definition
                # const_name =
                static_name = f"SWIG_{name}_{field.spelling}"  # const_name + "_decl"

                static_decl = rizin.stringify_decl(
                    field, pointee.get_result(), name=static_name
                )
                self.funcs.line(
                    f"static {static_decl}({args_outer_str}) {{",
                    f"    return SWIG{name}Director->{field.spelling}({args_inner_str});",
                    "}",
                )

                # %constant static func declaration
                const_decl = rizin.stringify_decl(field, field.type, name=static_name)
                self.consts.line(f"%constant {const_decl} = {static_name};")

            writer.line(
                f"{name}Director() {{}}",  # Constructor
                f"virtual ~{name}Director() {{}}",  # Destructor
            )

        writer.line("};")

    def write(self, writer: DirectWriter) -> None:
        """
        Writes self to DirectWriter
        """
        writer.line(f'%feature("director") {self.name}Director;')

        writer.line("%inline %{")
        with writer.indent():
            self.struct_writer.write(writer)

            writer.line(
                f"static {self.name}Director *SWIG{self.name}Director = NULL;",
            )
        writer.line("%}")

        writer.line("%{")
        with writer.indent():
            self.funcs.write(writer)
        writer.line("%}")

        self.consts.write(writer)

        # Python helper function
        writer.line("%pythoncode %{")
        writer.line(f"def register_{self.name}(plugin_class):")
        with writer.indent():
            writer.line("members = [")
            for data in self.data_members:
                with writer.indent():
                    writer.line(f'"{data}",')
            writer.line("]")

            writer.line("funcs = [")
            for func in self.func_members:
                with writer.indent():
                    writer.line(f'"{func}",')
            writer.line("]")

            writer.line(
                "plugin = plugin_class()",
                f"plugin_struct = {self.name}()",
                "for member in members:",
                "    if hasattr(plugin, member):",
                "        attr = getattr(plugin, member)",
                "        setattr(plugin_struct, member, attr)",
                "plugin_funcs = vars(plugin_class).keys()",
                "for func in funcs:",
                "    if func in plugin_funcs:",
                f"        name = f'SWIG_{self.name}_{{func}}'",
                "        attr = getattr(_rizin, name)",
                "        setattr(plugin_struct, func, attr)",
                "plugin.__disown__()",
                f"_rizin.cvar.SWIG{self.name}Director = plugin",
                "return plugin, plugin_struct",
            )
        writer.line("%}")
