"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List

from clang.wrapper import CursorKind, Func


class ModuleTypemap:
    activate: str
    deactivate: str

    args: List[str]

    def __init__(self, contents: str, *, activate: str, deactivate: str):
        self.activate = activate
        self.deactivate = deactivate

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
            f"Function {func.spelling} did not match typemap `{self.args}`",
            f"Contents were: {spellings}",
        )
