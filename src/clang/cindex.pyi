"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Tuple, Optional, Iterator

from enum import Enum

class Config:
    @staticmethod
    def set_library_path(path: str) -> None: ...

class Diagnostic:
    spelling: str
    location: SourceLocation

class TranslationUnit:
    PARSE_DETAILED_PROCESSING_RECORD: int

    @staticmethod
    def from_source(
        filename: str, args: List[str], options: Optional[int] = ...
    ) -> TranslationUnit: ...

    cursor: Cursor
    diagnostics: List[Diagnostic]

    def get_tokens(self, *, extent: SourceRange) -> Iterator[Token]: ...

class TranslationUnitLoadError(Exception): ...

### Type ###
class TypeKind(Enum):
    TYPEDEF: TypeKind
    ELABORATED: TypeKind

    POINTER: TypeKind
    CONSTANTARRAY: TypeKind
    FUNCTIONPROTO: TypeKind
    FUNCTIONNOPROTO: TypeKind
    INCOMPLETEARRAY: TypeKind

    RECORD: TypeKind
    ENUM: TypeKind

    VOID: TypeKind
    BOOL: TypeKind
    FLOAT: TypeKind
    DOUBLE: TypeKind
    LONGDOUBLE: TypeKind

    # Unsigned
    CHAR_U: TypeKind
    UCHAR: TypeKind
    CHAR16: TypeKind
    CHAR32: TypeKind
    USHORT: TypeKind
    UINT: TypeKind
    ULONG: TypeKind
    ULONGLONG: TypeKind
    # Signed
    CHAR_S: TypeKind
    SCHAR: TypeKind
    WCHAR: TypeKind
    SHORT: TypeKind
    INT: TypeKind
    LONG: TypeKind
    LONGLONG: TypeKind

class Type:
    kind: TypeKind
    spelling: str

    def get_declaration(self) -> Cursor: ...
    def get_pointee(self) -> Type: ...
    def get_canonical(self) -> Type: ...
    def get_named_type(self) -> Type: ...
    def get_array_element_type(self) -> Type: ...
    def get_result(self) -> Type: ...
    def argument_types(self) -> Iterator[Type]: ...
    def is_const_qualified(self) -> bool: ...

    element_count: int

### Cursor ###
class SourceLocation:
    class File:
        name: str

    file: File
    line: int
    column: int

    @staticmethod
    def from_position(
        tu: TranslationUnit, file: File, line: int, column: int
    ) -> SourceLocation: ...

class SourceRange:
    start: SourceLocation
    end: SourceLocation

    @staticmethod
    def from_locations(start: SourceLocation, end: SourceLocation) -> SourceRange: ...
    def __contains__(self, location: SourceLocation) -> bool: ...

class Token:
    spelling: str
    extent: SourceRange

class CursorKind(Enum):
    INCLUSION_DIRECTIVE: CursorKind
    MACRO_INSTANTIATION: CursorKind

    ENUM_DECL: CursorKind
    MACRO_DEFINITION: CursorKind
    STRUCT_DECL: CursorKind
    TYPEDEF_DECL: CursorKind
    FUNCTION_DECL: CursorKind

    FIELD_DECL: CursorKind
    UNION_DECL: CursorKind
    PARM_DECL: CursorKind
    ENUM_CONSTANT_DECL: CursorKind

    ANNOTATE_ATTR: CursorKind
    TYPE_REF: CursorKind
    PACKED_ATTR: CursorKind

class Cursor:
    kind: CursorKind
    spelling: str
    type: Type

    location: SourceLocation
    extent: SourceRange
    translation_unit: TranslationUnit

    def get_children(self) -> Iterator[Cursor]: ...
    def get_arguments(self) -> Iterator[Cursor]: ...
    def get_tokens(self) -> Iterator[Token]: ...

    underlying_typedef_type: Type
    result_type: Type
    enum_value: int
