"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, OrderedDict, DefaultDict, Set, Optional, TYPE_CHECKING

from clang.cindex import Cursor, CursorKind, SourceRange

from binding_func import GenericFunc
from binding_generic_specializations import generic_structs

if TYPE_CHECKING:
    from cparser_header import Header

generics: OrderedDict[str, "Generic"] = OrderedDict()


class Generic:
    """
    A C struct with generic functions
    """

    name: str
    header: "Header"
    pointer: bool  # If type comments should have a pointer

    methods: OrderedDict[str, GenericFunc]

    specializations: Set[str]

    python_methods: OrderedDict[str, List[str]]
    specialization_extensions: DefaultDict[str, List[str]]

    def __init__(
        self,
        header: "Header",
        typedef: str,
        *,
        pointer: bool = False,
        dependencies: Optional[List["Generic"]] = None,
    ):
        self.header = header
        self.name = typedef

        self.pointer = pointer
        self.dependencies = dependencies or []

        self.methods = OrderedDict()
        self.specializations = set()

        self.python_methods = OrderedDict()
        self.specialization_extensions = DefaultDict(list)

        assert typedef not in generics
        generics[typedef] = self

        typedef_cursor = header.pop(CursorKind.TYPEDEF_DECL, typedef)
        struct = typedef_cursor.underlying_typedef_type.get_declaration()
        assert (
            struct.kind == CursorKind.STRUCT_DECL
        ), "Typedef underlying declaration was {struct_cursor.kind}, not STRUCT_DECL"
        generic_structs[struct.spelling] = self

    def add_method(
        self,
        name: str,
        *,
        rename: str,
        generic_ret: bool = False,
        generic_args: Optional[Set[str]] = None,
    ) -> None:
        """
        Add C function with name as method
        """
        method = GenericFunc(
            self.header,
            name,
            generic_ret=generic_ret,
            generic_args=generic_args,
        )

        assert rename not in self.methods
        self.methods[rename] = method

    def add_specialization(self, cursor: Cursor) -> Optional[str]:
        """
        Add specialization from comment at cursor

        Returns None if no specialization found
        """
        # Extract type comment
        typeref = next(
            child
            for child in cursor.get_children()
            if child.kind == CursorKind.TYPE_REF
        )

        src_range = SourceRange.from_locations(typeref.extent.end, cursor.location)
        token = next(cursor.translation_unit.get_tokens(extent=src_range)).spelling

        if not token.startswith("/*<") or not token.endswith(">*/"):
            return None

        name = token[3:-3]
        if name.startswith("const "):
            name = name[len("const ") :]

        # Validate comment and add specialization
        if self.pointer:
            if name[-1] != "*":
                raise Exception(
                    f"Annotation for generic {self.name} at {cursor.location} lacks pointer"
                )
            if name[-2] != " ":
                raise Exception(
                    f"Annotation for generic {self.name} "
                    f"at {cursor.location} lacks space before pointer"
                )
            specialization = name[:-2]
        else:
            if name[-1] == "*":
                raise Exception(
                    f"Annotation for generic {self.name} at {cursor.location} has pointer"
                )
            specialization = name

        self.specializations.add(specialization)
        for dependency in self.dependencies:
            dependency.specializations.add(specialization)

        return specialization

    def add_python_method(self, decl: str, *lines: str) -> None:
        """
        Add python function with decl
        """
        self.python_methods[decl] = [f"def {decl}:"] + [f"    {line}" for line in lines]

    def add_specialization_extension(self, specialization: str, *lines: str) -> None:
        """
        Add lines to %extend only for specified specialization
        """
        self.specialization_extensions[specialization] += list(lines)
