"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only

Specifies a SWIG class
"""

from typing import List, Dict, Optional

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
from module import rizin
from module_func import ModuleFunc, FuncKind


class ModuleClass:
    """
    Represents a SWIG class

    Contains a struct and SWIG %extend
    """

    struct: Struct
    struct_writer: BufferedWriter
    funcs: List[ModuleFunc]

    def __init__(
        self,
        header: Header,
        *,
        typedef: Optional[str] = None,
        struct: Optional[str] = None,
        rename: Optional[str] = None,
        ignore_fields: Optional[List[str]] = None,
        rename_fields: Optional[Dict[str, str]] = None,
    ):
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

        if rename:
            self.struct_writer.line(
                f"typedef struct {struct_cursor.spelling} {rename};",
                f"%rename {struct_cursor.spelling} {rename};",
            )

        self.gen_struct(
            struct_cursor, ignore_fields=ignore_fields, rename_fields=rename_fields
        )

    def add_constructor(self, header: Header, name: str) -> None:
        header.used.add(name)

        func = ModuleFunc(
            header.funcs[name], FuncKind.CONSTRUCTOR, name=self.struct.spelling
        )
        self.funcs.append(func)

    def add_destructor(self, header: Header, name: str) -> None:
        header.used.add(name)

        func = ModuleFunc(
            header.funcs[name], FuncKind.DESTRUCTOR, name=self.struct.spelling
        )
        self.funcs.append(func)

    def add_method(
        self,
        header: Header,
        name: str,
        *,
        rename: Optional[str] = None,
        default_args: Optional[Dict[str, str]] = None,
    ) -> None:
        header.used.add(name)
        binderfunc = ModuleFunc(
            header.funcs[name], FuncKind.THIS, name=rename, default_args=default_args
        )
        self.funcs.append(binderfunc)

    def add_func(
        self,
        header: Header,
        name: str,
        *,
        rename: Optional[str] = None,
        default_args: Optional[Dict[str, str]] = None,
    ) -> None:
        header.used.add(name)
        binderfunc = ModuleFunc(
            header.funcs[name], FuncKind.STATIC, name=rename, default_args=default_args
        )
        self.funcs.append(binderfunc)

    def add_prefixed_methods(self, header: Header, prefix: str) -> None:
        """
        Adds functions with the specified prefix and who have $self
        as the first argument, as methods of the class
        """

        def predicate(func: Func) -> bool:
            if func.spelling in header.used:
                return False  # not used
            if not func.spelling.startswith(prefix):
                return False  # correct prefix
            if "RZ_API" not in func.attrs:
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
            binderfunc = ModuleFunc(
                func, FuncKind.THIS, name=func.spelling[len(prefix) :]
            )
            self.funcs.append(binderfunc)

    def add_prefixed_funcs(self, header: Header, prefix: str) -> None:
        """
        Adds functions with the specified prefix as static methods of the class
        """

        def predicate(func: Func) -> bool:
            if func.spelling in header.used:
                return False  # not used
            if not func.spelling.startswith(prefix):
                return False  # correct prefix
            if "RZ_API" not in func.attrs:
                return False  # RZ_API
            return True

        for func in filter(predicate, header.funcs.values()):
            header.used.add(func.spelling)
            modulefunc = ModuleFunc(
                func, FuncKind.STATIC, name=func.spelling[len(prefix) :]
            )
            self.funcs.append(modulefunc)

    def gen_struct(
        self,
        struct: Struct,
        *,
        ignore_fields: Optional[List[str]] = None,
        rename_fields: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Generates the struct portion of the class
        """
        fields = set()  # ensure all ignore/rename_fields are valid
        ignore_set = set(ignore_fields) if ignore_fields else set()
        writer = self.struct_writer

        # %rename fields
        rename_fields = rename_fields or {}
        for old, new in rename_fields.items():
            writer.line(f"%rename {struct.spelling}::{old} {new};")

        def gen_field(field: StructField) -> None:
            assert field.spelling not in fields
            fields.add(field.spelling)

            if field.spelling in ignore_set:
                return
            decl = rizin.stringify_decl(field, field.type)
            writer.line(f"{decl};")

        def gen_union(field: StructUnionField) -> None:
            assert field.spelling not in fields
            fields.add(field.spelling)

            if field.spelling in ignore_set:
                return
            writer.line("union {")
            with writer.indent():
                for union_field in field.get_children():
                    assert union_field.kind == CursorKind.FIELD_DECL
                    gen_field(union_field)
            writer.line("}")

        writer.line(f"struct {struct.spelling} {{")
        with writer.indent():
            for field in struct.get_children():
                if field.kind == CursorKind.STRUCT_DECL:
                    continue

                if field.kind == CursorKind.FIELD_DECL:
                    gen_field(field)
                elif field.kind == CursorKind.UNION_DECL:
                    gen_union(field)
                else:
                    raise Exception(
                        f"Unexpected struct child of kind: {field.kind} at {field.location}"
                    )
        writer.line("};")

        # sanity check
        for ignored_field in ignore_set:
            assert ignored_field in fields
        for renamed_field in rename_fields.keys():
            assert renamed_field in fields

        # un %rename fields
        for old in rename_fields.keys():
            writer.line(f'%rename {struct.spelling}::{old} "";')

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.struct_writer)

        writer.line(f"%extend {self.struct.spelling} {{")
        with writer.indent():
            for func in self.funcs:
                func.merge(writer)
        writer.line("}")
