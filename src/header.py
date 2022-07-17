"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only

Parses a rizin header
"""

from typing import List, OrderedDict, Set

import os

from clang.cindex import TranslationUnit
from clang.wrapper import Cursor, CursorKind, Macro, Var, Func, Struct, Enum, Typedef

from module import rizin


class Header:
    """
    Represents a header in the librz/includes directory
    """

    # Class variables
    clang_args: List[str] = []
    rizin_inc_path: str

    name: str

    nodes: OrderedDict[str, Cursor]
    used: Set[str]

    macros: OrderedDict[str, Macro]
    variables: OrderedDict[str, Var]
    funcs: OrderedDict[str, Func]
    structs: OrderedDict[str, Struct]
    enums: OrderedDict[str, Enum]
    typedefs: OrderedDict[str, Typedef]

    def __init__(self, header_name: str):
        rizin.headers.add(self)
        self.name = header_name

        translation_unit = TranslationUnit.from_source(
            filename="main.c",
            unsaved_files=[("main.c", f"#include <{header_name}>")],
            args=Header.clang_args,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )

        for diag in translation_unit.diagnostics:
            print(diag)

        self.nodes = OrderedDict()
        self.used = set()

        self.macros = OrderedDict()
        self.variables = OrderedDict()
        self.funcs = OrderedDict()
        self.structs = OrderedDict()
        self.enums = OrderedDict()
        self.typedefs = OrderedDict()

        filename = os.path.join(
            Header.rizin_inc_path, header_name
        )  # Current header name
        for cursor in translation_unit.cursor.get_children():
            # Skip nodes from other headers
            if not cursor.location.file or cursor.location.file.name != filename:
                continue

            # Skip `#include` and macro expansion
            if cursor.kind in [
                CursorKind.INCLUSION_DIRECTIVE,
                CursorKind.MACRO_INSTANTIATION,
            ]:
                continue

            # Rename anonymous declarations and check for redefinitions
            name = cursor.spelling
            if not name:
                if cursor.kind not in [
                    CursorKind.STRUCT_DECL,
                    CursorKind.ENUM_DECL,
                ]:
                    raise Exception(
                        f"Unexpected anonymous symbol of kind: {cursor.kind} at {cursor.location}"
                    )
                name = f"anonymous_node_{len(self.nodes)}"
            elif cursor.spelling in self.nodes:  # Redefinition
                if cursor.kind == CursorKind.STRUCT_DECL:
                    prev = self.nodes[cursor.spelling]
                    assert prev.kind == CursorKind.STRUCT_DECL
                    assert not any(prev.get_children())  # Should be forward declaration
                else:
                    raise Exception(
                        f"Unexpected redefinition of symbol: {cursor.spelling}, "
                        f"of kind: {cursor.kind} at {cursor.location}"
                    )

            # Add to nodes OrderedDict
            self.nodes[cursor.spelling] = cursor

            # Add to specific kind OrderedDict
            if cursor.kind == CursorKind.MACRO_DEFINITION:
                self.macros[name] = cursor
            elif cursor.kind == CursorKind.VAR_DECL:
                self.variables[name] = cursor
            elif cursor.kind == CursorKind.FUNCTION_DECL:
                self.funcs[name] = cursor
            elif cursor.kind == CursorKind.STRUCT_DECL:
                self.structs[name] = cursor
            elif cursor.kind == CursorKind.ENUM_DECL:
                self.enums[name] = cursor
            elif cursor.kind == CursorKind.TYPEDEF_DECL:
                self.typedefs[name] = cursor
            else:
                raise Exception(
                    f"Unexpected toplevel node of kind: {str(cursor.kind)} at {cursor.location}"
                )

    def ignore(self, *names: str) -> None:
        for name in names:
            assert name in self.nodes
            assert name not in self.used
            self.used.add(name)
