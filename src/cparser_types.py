"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Optional, Union, NoReturn, TYPE_CHECKING

from clang.cindex import Cursor, Type, TypeKind

if TYPE_CHECKING:
    from binding_generic import Generic


class CBaseType:
    """
    Base class for type wrapper
    """

    type_: Type

    def __init__(self, type_: Type):
        self.type_ = type_


class CPrimitiveType(CBaseType):
    """
    Primitive type wrapper
    """


class CPointerType(CBaseType):
    """
    Pointer type wrapper
    """

    pointee: "CType"

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.pointee = wrap_type(type_.get_pointee())


class CIncompleteArrayType(CBaseType):
    """
    Array type wrapper without size (eg. int[])
    """

    element: "CType"

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.element = wrap_type(type_.get_array_element_type())


class CFixedArrayType(CIncompleteArrayType):
    """
    Array type wrapper with fixed size (eg. int[10])
    """

    element_count: int

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.element_count = type_.element_count


class CTypedefType(CBaseType):
    """
    Typedef type wrapper
    """

    canonical: "CType"
    cursor: Cursor

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.canonical = wrap_type(type_.get_canonical())
        self.cursor = type_.get_declaration()


class CRecordType(CBaseType):
    """
    Struct type wrapper

    Structs without a name (eg. typedef struct {} AStruct)
    use their typedef name for decl_spelling
    """

    decl_spelling: str
    generic: Optional["Generic"]
    specialization: Optional[str]

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.decl_spelling = type_.get_declaration().spelling or type_.spelling
        if self.decl_spelling.startswith("const "):
            self.decl_spelling = self.decl_spelling[len("const ") :]
        self.generic = None
        self.specialization = None


class CFunctionType(CBaseType):
    """
    Function type wrapper
    """

    result: "CType"
    args: List["CType"]
    arg_names: Optional[List[str]]

    def __init__(self, type_: Type):
        super().__init__(type_)
        self.result = wrap_type(type_.get_result())
        self.args = [wrap_type(arg) for arg in type_.argument_types()]
        self.arg_names = None


CType = Union[
    CPrimitiveType,
    CRecordType,
    CPointerType,
    CFunctionType,
    CIncompleteArrayType,
    CFixedArrayType,
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
        return CPointerType(type_)
    if type_.kind == TypeKind.CONSTANTARRAY:
        return CFixedArrayType(type_)
    if type_.kind == TypeKind.INCOMPLETEARRAY:
        return CIncompleteArrayType(type_)
    if type_.kind == TypeKind.TYPEDEF:
        return CTypedefType(type_)
    if type_.kind == TypeKind.FUNCTIONPROTO:
        return CFunctionType(type_)
    if type_.kind == TypeKind.RECORD:
        return CRecordType(type_)

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
