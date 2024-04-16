"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import List, Dict, OrderedDict, Set, Optional, overload

from dataclasses import dataclass

from clang.cindex import CursorKind

from cparser_header import Header
from cparser_types import CType, CPointerType, CTypedefType, CRecordType, wrap_type
from binding_func import Func
from binding_generic_specializations import gen_ctype_specializations
from binding_typemap import Typemap

classes: OrderedDict[str, "Class"] = OrderedDict()
class_structs: Dict[str, "Class"] = {}


@dataclass
class Field:
    """
    Groups a field name and type
    """

    name: str
    rename: Optional[str]
    ctype: CType


class Class:
    """
    A collection of fields, static functions, and methods wrapping a C struct
    """

    name: str
    struct_name: str
    header: Header

    fields: OrderedDict[str, Field]
    funcs: OrderedDict[str, Func]
    methods: OrderedDict[str, Func]

    constructor: Optional[Func]
    destructor: Optional[Func]

    @overload
    def __init__(
        self,
        header: Header,
        *,
        typedef: str,
        ignore_fields: Optional[Set[str]] = ...,
        rename_fields: Optional[Dict[str, str]] = ...,
    ):
        ...

    @overload
    def __init__(
        self,
        header: Header,
        *,
        typedef: str,
        struct: str,
        ignore_fields: Optional[Set[str]] = ...,
        rename_fields: Optional[Dict[str, str]] = ...,
    ):
        ...

    def __init__(
        self,
        header: Header,
        *,
        typedef: str,
        struct: Optional[str] = None,
        ignore_fields: Optional[Set[str]] = None,
        rename_fields: Optional[Dict[str, str]] = None,
    ):
        self.header = header
        self.name = typedef

        self.fields = OrderedDict()
        self.funcs = OrderedDict()
        self.methods = OrderedDict()
        self.constructor = None
        self.destructor = None

        # Get struct cursor from header
        if not struct:
            typedef_cursor = header.pop(CursorKind.TYPEDEF_DECL, typedef)
            struct_cursor = typedef_cursor.underlying_typedef_type.get_declaration()
            assert (
                struct_cursor.kind == CursorKind.STRUCT_DECL
            ), "Typedef underlying declaration was {struct_cursor.kind}, not STRUCT_DECL"
        else:
            struct_cursor = header.pop(CursorKind.STRUCT_DECL, struct)

        self.struct_name = struct_cursor.spelling or typedef

        assert typedef not in classes
        classes[typedef] = self
        class_structs[self.struct_name] = self

        # Parse struct fields
        for field in struct_cursor.get_children():
            if field.kind == CursorKind.FIELD_DECL:
                name = field.spelling
                if ignore_fields and name in ignore_fields:
                    ignore_fields.remove(name)
                    continue

                if rename_fields:
                    rename = rename_fields.pop(name, None)
                else:
                    rename = None

                assert name not in self.fields
                ctype = wrap_type(field.type)
                gen_ctype_specializations([field], ctype)
                self.fields[name] = Field(name, rename, ctype)

            elif field.kind not in [CursorKind.STRUCT_DECL, CursorKind.UNION_DECL]:
                raise Exception(
                    f"Unexpected struct child of kind: {field.kind} at {field.location}"
                )

        # Ensure all ignore_fields and rename_fields are for valid fields
        if ignore_fields and len(ignore_fields) != 0:
            print(
                f"[WARNING] Ignored fields on class {self.name} do not exist:",
                ", ".join(ignore_fields),
            )
        if rename_fields and len(rename_fields) != 0:
            print(
                f"[WARNING] Renamed fields on class {self.name} do not exist:",
                ", ".join(rename_fields),
            )

    def add_constructor(self, name: str) -> None:
        """
        Set C function with name as class constructor
        """
        assert not self.constructor
        self.constructor = Func(self.header, name)

    def add_destructor(self, name: str) -> None:
        """
        Set C function with name as class destructor
        """
        assert not self.destructor
        self.destructor = Func(self.header, name)

    def add_func(
        self,
        name: str,
        *,
        rename: str,
        default_args: Optional[Dict[str, str]] = None,
        typemaps: Optional[List[Typemap]] = None,
    ) -> None:
        """
        Add C function with name as static function
        """
        func = Func(
            self.header,
            name,
            default_args=default_args,
            typemaps=typemaps,
        )

        assert rename not in self.funcs
        self.funcs[rename] = func

    def add_method(
        self,
        name: str,
        *,
        rename: str,
        default_args: Optional[Dict[str, str]] = None,
        typemaps: Optional[List[Typemap]] = None,
    ) -> None:
        """
        Add C function with name as method
        """
        method = Func(
            self.header,
            name,
            default_args=default_args,
            typemaps=typemaps,
        )

        assert rename not in self.methods
        self.methods[rename] = method

    def add_prefixed_methods(self, prefix: str) -> None:
        """
        Add C functions with a given prefix, and that take a
        pointer to this class as the first argument, as methods

        New names will be the function names with the prefix removed

        Note that this may result in names beginning with numbers
        (eg. rz_reg_64_to_32 -> 64_to_32) which need to be manually added
        """
        method_names = set()
        for name, cfunc in self.header.cfuncs.items():
            if not name.startswith(prefix):
                continue
            if "RZ_API" not in cfunc.attrs:
                continue
            if len(cfunc.args) == 0:
                continue

            # Select functions with class struct as first argument
            ctype = cfunc.args[0].ctype
            if not isinstance(ctype, CPointerType):
                continue

            ctype = ctype.pointee
            if isinstance(ctype, CTypedefType):
                ctype = ctype.canonical

            if not isinstance(ctype, CRecordType):
                continue

            if ctype.decl_spelling != self.struct_name:
                continue

            rename = name[len(prefix) :]
            method = Func(
                self.header,
                cfunc=cfunc,
            )

            method_names.add(name)
            assert rename not in self.methods
            self.methods[rename] = method

        self.header.ignore(*method_names)

    def add_prefixed_funcs(self, prefix: str) -> None:
        """
        Add C functions with a given prefix as static functions
        """
        func_names = set()
        for name, cfunc in self.header.cfuncs.items():
            if not name.startswith(prefix):
                continue
            if "RZ_API" not in cfunc.attrs:
                continue

            rename = name[len(prefix) :]
            func = Func(
                self.header,
                cfunc=cfunc,
            )

            func_names.add(name)
            assert rename not in self.funcs
            self.funcs[rename] = func

        self.header.ignore(*func_names)
