"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import Optional

from clang.wrapper import CursorKind

from header import Header
from module import rizin
from writer import BufferedWriter, DirectWriter


class ModuleEnum:
    """
    Represents a SWIG enum

    Can be constructed from macro definitions or a C enum
    """

    buf: BufferedWriter

    def __init__(
        self,
        header: Header,
        *names: str,
        prefix: Optional[str] = None,
        typedef: Optional[str] = None,
    ):
        rizin.enums.append(self)

        buf = BufferedWriter()
        self.buf = buf

        for name in names:
            self.add_macro(header, name)

        if prefix:
            for name in header.macros.keys():
                if name.startswith(prefix):
                    self.add_macro(header, name)

        if typedef:
            typedef_cursor = header.typedefs[typedef]
            enum_cursor = typedef_cursor.underlying_typedef_type.get_declaration()
            assert enum_cursor.kind == CursorKind.ENUM_DECL

            buf.line(f"enum {typedef_cursor.spelling} {{")
            with buf.indent():
                for field in enum_cursor.get_children():
                    assert field.kind == CursorKind.ENUM_CONSTANT_DECL
                    buf.line(f"{field.spelling} = {field.enum_value},")
            buf.line("};")

    def add_macro(self, header: Header, name: str) -> None:
        """
        Adds a C macro with the specified name to self.buf
        """
        macro = header.macros[name]
        toks = [tok.spelling for tok in macro.get_tokens()]
        assert toks[0] == name
        definition = " ".join(toks[1:])
        self.buf.line(f"#define {name} {definition}")

    def write(self, writer: DirectWriter) -> None:
        """
        Writes self to DirectWriter
        """
        self.buf.write(writer)
