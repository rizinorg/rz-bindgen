"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, OrderedDict, Optional, overload

from clang.cindex import Cursor, CursorKind

from cparser_header import Header

enums: List["Enum"] = []
macro_enums: List["MacroEnum"] = []


class Enum:
    """
    A C enum
    """

    typedef_name: str
    fields: OrderedDict[str, str]

    def __init__(self, header: Header, *, typedef: str):
        enums.append(self)

        typedef_cursor = header.pop(CursorKind.TYPEDEF_DECL, typedef)
        self.typedef_name = typedef_cursor.spelling

        enum = typedef_cursor.underlying_typedef_type.get_declaration()
        assert (
            enum.kind == CursorKind.ENUM_DECL
        ), "Typedef underlying declaration was {struct_cursor.kind}, not ENUM_DECL"

        self.fields = OrderedDict()
        for field in enum.get_children():
            assert field.kind == CursorKind.ENUM_CONSTANT_DECL
            self.fields[field.spelling] = str(field.enum_value)


class MacroEnum:
    """
    A C enum consisting of #define's
    """

    defines: OrderedDict[str, str]

    @overload
    def __init__(self, header: Header, *defines: str):
        ...

    @overload
    def __init__(self, header: Header, *, prefix: str):
        ...

    def __init__(
        self,
        header: Header,
        *defines: str,
        prefix: Optional[str] = None,
    ):
        macro_enums.append(self)

        self.defines = OrderedDict()

        def add_definition(macro: Cursor) -> None:
            toks = [tok.spelling for tok in macro.get_tokens()]
            definition = " ".join(toks[1:])
            self.defines[macro.spelling] = definition

        if prefix:
            macro_names = []
            for name, macro in header.cursors[CursorKind.MACRO_DEFINITION].items():
                if name.startswith(prefix):
                    macro_names.append(name)
                    add_definition(macro)
            header.ignore(*macro_names)

        for define in defines:
            add_definition(header.pop(CursorKind.MACRO_DEFINITION, define))
