"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List

from clang.wrapper import CursorKind, Func
from writer import DirectWriter


class ModuleTypemap:
    """
    Represents a SWIG typemap

    To activate the typemap, the macro %{typemap_name}_activate
    is called with the provided typemap args

    To deactivate the typemap, the macro %{typemap_name}_deactivate
    is called with the provided typemap args

    The macros should be defined in the rizin_lib.i file
    """

    name: str
    contents: str
    args: List[str]

    def __init__(self, name: str, contents: str):
        self.name = name
        self.contents = contents
        self.args = contents.split(", ")

    def check(self, func: Func) -> None:
        index = 0
        spellings = []
        for arg in func.get_arguments():
            assert arg.kind == CursorKind.PARM_DECL

            spelling = f"{arg.type.spelling} {arg.spelling}"
            if spelling.startswith("const "):
                spelling = spelling[len("const ") :]
            spellings.append(spelling)

            if spelling == self.args[index]:
                index += 1
                if index == len(self.args):
                    return
            else:
                index = 0

        raise Exception(
            f"Function {func.spelling} did not match typemap `{self.args}`. "
            f"Contents were: {spellings}"
        )

    def merge_activate(self, writer: DirectWriter) -> None:
        writer.line(f"%{self.name}_activate({self.contents});")

    def merge_deactivate(self, writer: DirectWriter) -> None:
        writer.line(f"%{self.name}_deactivate({self.contents});")
