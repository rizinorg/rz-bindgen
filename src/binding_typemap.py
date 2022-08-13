"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, TYPE_CHECKING

from dataclasses import dataclass

if TYPE_CHECKING:
    from binding_func import Func


@dataclass
class TypemapArg:
    """
    Groups a typemap argument name and its type
    """

    type_: str
    name: str


class Typemap:
    """
    A transformation applied to a function with arguments
    that match a name and type
    """

    name: str
    args: List[TypemapArg]

    def __init__(self, name: str, args: List[TypemapArg]):
        self.name = name
        self.args = args

    def check(self, func: "Func") -> None:
        """
        Check if a typemap applies to a function
        """
        args = [
            TypemapArg(arg.ctype.type_.spelling, arg.cursor.spelling)
            for arg in func.cfunc.args
        ]

        num_args = len(self.args)
        for start in range(len(args) - num_args + 1):
            for typemap_arg, arg in zip(self.args, args[start : start + num_args]):
                if typemap_arg != arg:
                    break
            else:
                return

        raise Exception(
            f"Function {func.cfunc.cursor.spelling} did not match typemap `{self.args}`. "
            f"Contents were: {args}"
        )


buffer_len_typemap = Typemap(
    "buffer_len",
    [TypemapArg("unsigned char *", "buf"), TypemapArg("unsigned long long", "len")],
)

const_buffer_len_typemap = Typemap(
    "const_buffer_len",
    [
        TypemapArg("const unsigned char *", "buf"),
        TypemapArg("unsigned long long", "len"),
    ],
)
