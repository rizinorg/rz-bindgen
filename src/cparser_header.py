"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, OrderedDict, DefaultDict, Set, Optional

from functools import cached_property
import os

from clang.cindex import TranslationUnit, Cursor, CursorKind

from cparser_types import CType, wrap_type


### Cursor wrappers ###
class AttrCursor:
    """
    Base class for cursor wrapper with attributes
    """

    cursor: Cursor

    def __init__(self, cursor: Cursor):
        self.cursor = cursor

    @cached_property
    def attrs(self) -> Set[str]:
        """
        Get annotation __attribute__'s on cursor
        """
        return {
            child.spelling
            for child in self.cursor.get_children()
            if child.kind == CursorKind.ANNOTATE_ATTR
        }


class CFuncArg(AttrCursor):
    """
    Function argument cursor wrapper
    """

    default: Optional[str]

    def __init__(self, cursor: Cursor):
        super().__init__(cursor)
        self.default = None

    @cached_property
    def ctype(self) -> CType:
        """
        Get wrapped arg type
        """
        return wrap_type(self.cursor.type)


class CFunc(AttrCursor):
    """
    Function declaration cursor wrapper
    """

    @cached_property
    def args(self) -> List[CFuncArg]:
        """
        Get function args
        """
        return [CFuncArg(arg) for arg in self.cursor.get_arguments()]

    @cached_property
    def result_ctype(self) -> CType:
        """
        Get wrapped result type
        """
        return wrap_type(self.cursor.result_type)


### Configuration ###
rizin_include_path: Optional[str] = None
clang_args: List[str] = []

### Headers ###
headers: List["Header"] = []


class HeaderBuilder:
    """
    Builder class for Header, enabling parallel calls to libclang
    """

    name: str
    filename: str
    extra_filename: Optional[str]

    def __init__(self, name: str):
        self.name = name
        name_segments = name.split("/")

        assert rizin_include_path
        filename = os.path.abspath(os.path.join(rizin_include_path, *name_segments))

        # Fix sdb path if using source librz/include
        if name_segments[0] == "sdb" and not os.path.exists(filename):
            name_segments = ["..", "util", "sdb", "src"] + name_segments[1:]
            filename = os.path.abspath(os.path.join(rizin_include_path, *name_segments))

        assert os.path.exists(filename)
        self.filename = filename

        # Parse ht_inc.h if importing SDB hashtable header
        self.extra_filename = None
        if name_segments[-1] in ["ht_pp.h", "ht_pu.h", "ht_up.h", "ht_uu.h"]:
            self.extra_filename = "ht_inc.h"

    def translation_unit(self) -> TranslationUnit:
        """
        Creates TranslationUnit (for use in the build method)

        TranslationUnit.from_source is parallelizable since ctypes
        releases the GIL, so we leave it to the caller to call this
        method in parallel and later call build sequentially.
        """
        return TranslationUnit.from_source(
            filename=self.filename,
            args=clang_args,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )

    def build(self, translation_unit: TranslationUnit) -> "Header":
        """
        Build the Header instance
        """
        return Header(translation_unit, self)


class Header:
    """
    A parsed C header file
    """

    name: str

    cursors: DefaultDict[CursorKind, OrderedDict[str, Cursor]]
    cursor_kinds: OrderedDict[str, CursorKind]
    cfuncs: OrderedDict[str, CFunc]  # Store __attributes__

    def __init__(self, translation_unit: TranslationUnit, builder: HeaderBuilder):
        headers.append(self)

        self.name = builder.name

        self.cursors = DefaultDict(OrderedDict)
        self.cursor_kinds = OrderedDict()
        self.cfuncs = OrderedDict()

        for cursor in translation_unit.cursor.get_children():
            cursor_file = cursor.location.file
            if not cursor_file:
                continue

            # Skip nodes from other headers
            cursor_file_name = cursor_file.name
            if cursor_file_name != builder.filename and not (
                builder.extra_filename
                and cursor_file_name.endswith(builder.extra_filename)
            ):
                continue

            # Skip `#include` and macro expansion
            if cursor.kind in [
                CursorKind.INCLUSION_DIRECTIVE,
                CursorKind.MACRO_INSTANTIATION,
            ]:
                continue

            # Ignore anonymous declarations
            name = cursor.spelling
            if not name:
                continue

            # Check for redefinitions
            if name in self.cursor_kinds:  # Redefinition
                prev = self.cursors[cursor.kind][name]
                if cursor.kind == CursorKind.STRUCT_DECL:
                    assert prev.kind == CursorKind.STRUCT_DECL
                    assert not any(prev.get_children())  # Should be forward declaration
                elif cursor.kind == CursorKind.MACRO_DEFINITION:
                    assert prev.kind == CursorKind.MACRO_DEFINITION
                    basename = os.path.basename(cursor_file_name)
                    assert (basename, name) in [
                        ("rz_types.h", "__WINDOWS__")
                    ], f"Unexpected redefinition of macro {name} in file {basename}"
                else:
                    raise Exception(
                        f"Unexpected redefinition of symbol: {name}, "
                        f"of kind: {cursor.kind} at {cursor.location}"
                    )

            self.cursor_kinds[name] = cursor.kind
            if cursor.kind == CursorKind.FUNCTION_DECL:
                self.cfuncs[name] = CFunc(cursor)
            else:
                self.cursors[cursor.kind][name] = cursor

    def pop(self, kind: CursorKind, name: str) -> Cursor:
        """
        Remove and return a cursor with the given name and kind
        """
        return self.cursors[kind].pop(name)

    def pop_func(self, name: str) -> CFunc:
        """
        Remove and return a CFunc with the given name and kind
        """
        return self.cfuncs.pop(name)

    def ignore(self, *names: str, prefix: Optional[str] = None) -> None:
        """
        Remove cursors and CFuncs with the given names
        or that have the given prefix
        """
        names_list = list(names)

        if prefix:
            for name in self.cursor_kinds:
                if name.startswith(prefix):
                    names_list.append(name)

        for name in names_list:
            kind = self.cursor_kinds.pop(name)
            if kind == CursorKind.FUNCTION_DECL:
                self.pop_func(name)
            else:
                self.pop(kind, name)
