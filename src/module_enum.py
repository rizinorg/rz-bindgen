"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import Optional

from header import Header
from module import rizin
from writer import BufferedWriter, DirectWriter


class ModuleEnum:
    buf: BufferedWriter

    def __init__(self, header: Header, *names: str, prefix: Optional[str] = None):
        rizin.enums.append(self)

        buf = BufferedWriter()
        self.buf = buf

        for name in names:
            self.add_macro(header, name)

        if prefix:
            for name in header.macros.keys():
                if name.startswith(prefix):
                    self.add_macro(header, name)

    def add_macro(self, header: Header, name: str) -> None:
        macro = header.macros[name]
        toks = [tok.spelling for tok in macro.get_tokens()]
        assert toks[0] == name
        definition = " ".join(toks[1:])
        self.buf.line(f"#define {name} {definition}")

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.buf)
