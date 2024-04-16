"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Dict, Set, Optional, overload, TYPE_CHECKING

from binding_typemap import Typemap
from binding_generic_specializations import gen_ctype_specializations

if TYPE_CHECKING:
    from cparser_header import Header, CFunc


class Func:
    """
    A wrapped C function
    """

    cfunc: "CFunc"
    typemaps: List[Typemap]

    @overload
    def __init__(
        self,
        header: "Header",
        name: str,
        *,
        default_args: Optional[Dict[str, str]] = ...,
        typemaps: Optional[List[Typemap]] = ...,
    ):
        ...

    @overload
    def __init__(
        self,
        header: "Header",
        *,
        cfunc: "CFunc",
        default_args: Optional[Dict[str, str]] = ...,
        typemaps: Optional[List[Typemap]] = ...,
    ):
        ...

    def __init__(
        self,
        header: "Header",
        name: Optional[str] = None,
        *,
        cfunc: Optional["CFunc"] = None,
        default_args: Optional[Dict[str, str]] = None,
        typemaps: Optional[List[Typemap]] = None,
    ):
        if name:
            cfunc = header.pop_func(name)
        assert cfunc

        for arg in cfunc.args:
            arg_name = arg.cursor.spelling
            if default_args and arg_name in default_args:
                arg.default = default_args[arg_name]
                default_args.pop(arg_name)
        assert not default_args or len(default_args) == 0

        self.cfunc = cfunc
        self.typemaps = typemaps or []
        self.gen_ctype_specializations()

        for typemap in self.typemaps:
            typemap.check(self)

    def gen_ctype_specializations(self) -> None:
        """
        Generate generic specializations for args and return type
        """
        for arg in self.cfunc.args:
            gen_ctype_specializations([arg.cursor], arg.ctype)
        gen_ctype_specializations([self.cfunc.cursor], self.cfunc.result_ctype)


class GenericFunc(Func):
    """
    A wrapped C function with generic args or a generic return value
    """

    generic_ret: bool
    generic_args: Set[str]

    def __init__(
        self,
        header: "Header",
        name: str,
        *,
        generic_ret: bool = False,
        generic_args: Optional[Set[str]] = None,
    ):
        self.generic_ret = generic_ret
        self.generic_args = generic_args or set()
        super().__init__(header, name)

    def gen_ctype_specializations(self) -> None:
        if not self.generic_ret:
            gen_ctype_specializations([self.cfunc.cursor], self.cfunc.result_ctype)

        generic_args = self.generic_args.copy()

        for arg in self.cfunc.args[1:]:
            arg_name = arg.cursor.spelling
            if arg_name in generic_args:
                generic_args.remove(arg_name)
            else:
                gen_ctype_specializations([arg.cursor], arg.ctype)

        # Ensure all generic_args are for valid args
        assert len(generic_args) == 0
