"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Optional, Union, NoReturn, TYPE_CHECKING

from dataclasses import dataclass

from clang.cindex import Cursor, Type, TypeKind

if TYPE_CHECKING:
    from binding_generic import Generic


@dataclass
class CBaseType:
    """
    Base class for type wrapper
    """

    type_: Type


@dataclass
class CPrimitiveType(CBaseType):
    """
    Primitive type wrapper
    """


@dataclass
class CPointerType(CBaseType):
    """
    Pointer type wrapper
    """

    pointee: "CType"


@dataclass
class CArrayType(CBaseType):
    """
    Array type wrapper

    If fixed size (eg. char[80]), element_count is an int.
    If variable size (eg. char[]), element_count is None.
    """

    element: "CType"
    element_count: Optional[int] = None


@dataclass
class CTypedefType(CBaseType):
    """
    Typedef type wrapper
    """

    canonical: "CType"
    cursor: Cursor


@dataclass
class CRecordType(CBaseType):
    """
    Struct type wrapper

    Structs without a name (eg. typedef struct {} AStruct)
    use their typedef name for decl_spelling
    """

    decl_spelling: str
    generic: Optional["Generic"] = None
    specialization: Optional[str] = None


@dataclass
class CFunctionType(CBaseType):
    """
    Function type wrapper
    """

    result: "CType"
    args: List["CType"]
    arg_names: Optional[List[str]] = None


CType = Union[
    CPrimitiveType,
    CRecordType,
    CPointerType,
    CFunctionType,
    CArrayType,
    CTypedefType,
]


def wrap_type(type_: Type) -> CType:
    """
    Wrap a type
    """
    while type_.kind == TypeKind.ELABORATED:
        type_ = type_.get_named_type()

    # Complex types
    if type_.kind == TypeKind.POINTER:
        return CPointerType(type_, pointee=wrap_type(type_.get_pointee()))

    if type_.kind in [TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY]:
        array_t = CArrayType(type_, element=wrap_type(type_.get_array_element_type()))
        if type_.kind == TypeKind.CONSTANTARRAY:
            array_t.element_count = type_.element_count
        return array_t

    if type_.kind == TypeKind.TYPEDEF:
        return CTypedefType(
            type_,
            canonical=wrap_type(type_.get_canonical()),
            cursor=type_.get_declaration(),
        )

    if type_.kind == TypeKind.FUNCTIONPROTO:
        return CFunctionType(
            type_,
            result=wrap_type(type_.get_result()),
            args=[wrap_type(arg) for arg in type_.argument_types()],
        )

    if type_.kind == TypeKind.RECORD:
        decl_spelling = type_.get_declaration().spelling or type_.spelling
        if decl_spelling.startswith("const "):
            decl_spelling = decl_spelling[len("const ") :]

        return CRecordType(type_, decl_spelling=decl_spelling)

    # Primitive types
    if type_.kind in [
        TypeKind.ENUM,
        TypeKind.VOID,
        TypeKind.BOOL,
        TypeKind.FLOAT,
        TypeKind.DOUBLE,
        TypeKind.LONGDOUBLE,
        # Unsigned
        TypeKind.CHAR_U,
        TypeKind.UCHAR,
        TypeKind.CHAR16,
        TypeKind.CHAR32,
        TypeKind.USHORT,
        TypeKind.UINT,
        TypeKind.ULONG,
        TypeKind.ULONGLONG,
        # Signed
        TypeKind.CHAR_S,
        TypeKind.SCHAR,
        TypeKind.WCHAR,
        TypeKind.SHORT,
        TypeKind.INT,
        TypeKind.LONG,
        TypeKind.LONGLONG,
    ]:
        return CPrimitiveType(type_)
    raise Exception(f"Unknown type kind {type_.kind}")


def assert_never(_: NoReturn) -> NoReturn:
    """
    Helper to typecheck exhaustiveness
    """
    assert False
