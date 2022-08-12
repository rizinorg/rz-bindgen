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
        attrs = set()
        for child in self.cursor.get_children():
            if child.kind == CursorKind.ANNOTATE_ATTR:
                attrs.add(child.spelling)
        return attrs


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


class Header:
    """
    A parsed C header file
    """

    name: str
    files: Set[str]
    translation_unit: TranslationUnit

    cursors: DefaultDict[CursorKind, OrderedDict[str, Cursor]]
    cursor_kinds: OrderedDict[str, CursorKind]
    cfuncs: OrderedDict[str, CFunc]  # Store __attributes__

    def __init__(self, name: str):
        headers.append(self)

        self.name = name
        name_segments = name.split("/")

        assert rizin_include_path
        filename = os.path.abspath(os.path.join(rizin_include_path, *name_segments))

        # Fix sdb path
        if name_segments[0] == "sdb" and not os.path.exists(filename):
            name_segments = ["..", "util", "sdb", "src"] + name_segments[1:]
            filename = os.path.abspath(os.path.join(rizin_include_path, *name_segments))
        assert os.path.exists(filename)

        # Support ht_inc.h
        self.files = set([filename])
        if name_segments[-1] in ["ht_pp.h", "ht_pu.h", "ht_up.h", "ht_uu.h"]:
            name_segments[-1] = "ht_inc.h"
            self.files.add(
                os.path.abspath(os.path.join(rizin_include_path, *name_segments))
            )

        self.translation_unit = TranslationUnit.from_source(
            filename=filename,
            args=clang_args,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )

    def process(self) -> "Header":
        """
        Process header cursors

        TranslationUnit.from_source can be parallelized, but cursor.get_children
        cannot, so we split them
        """
        self.cursors = DefaultDict(OrderedDict)
        self.cursor_kinds = OrderedDict()
        self.cfuncs = OrderedDict()

        for cursor in self.translation_unit.cursor.get_children():
            # Skip nodes from other headers
            if not cursor.location.file or cursor.location.file.name not in self.files:
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
                assert cursor.kind in [
                    CursorKind.STRUCT_DECL,
                    CursorKind.ENUM_DECL,
                    CursorKind.UNION_DECL,
                ], f"Unexpected anonymous symbol of kind: {cursor.kind} at {cursor.location}"
                name = f"anonymous_node_{len(self.cursors)}"
            elif name in self.cursor_kinds:  # Redefinition
                prev = self.cursors[cursor.kind][name]
                if cursor.kind == CursorKind.STRUCT_DECL:
                    assert prev.kind == CursorKind.STRUCT_DECL
                    assert not any(prev.get_children())  # Should be forward declaration
                elif cursor.kind == CursorKind.MACRO_DEFINITION:
                    assert prev.kind == CursorKind.MACRO_DEFINITION
                    assert name.startswith(
                        "__"
                    )  # TODO: better detection of redefined macros
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

        return self

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
