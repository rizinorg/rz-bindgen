"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

import os
from enum import Enum as PyEnum

from clang.cindex import TypeKind

from cparser_header import headers
from cparser_types import (
    CType,
    CPointerType,
    CRecordType,
    CFunctionType,
    CArrayType,
    CTypedefType,
    CPrimitiveType,
    assert_never,
)
from binding_generic import Generic, generics
from binding_generic_specializations import generic_structs
from binding_class import Class, classes, class_structs
from binding_func import Func, GenericFunc
from binding_director import Director, directors
from binding_enum import Enum, enums, macro_enums
from writer import Writer


def generate(output_dir: str) -> None:
    """
    Generate SWIG bindings and write to output_dir/rizin.i
    """
    output_path = os.path.join(output_dir, "rizin.i")
    with open(output_path, "w", encoding="utf-8") as output_file:
        write(Writer(output_file))


def write(writer: Writer) -> None:
    """
    Toplevel SWIG generator
    """
    writer.line("%module(directors=1) rizin")
    writer.line("%{")
    for header in headers:
        writer.line(f"#include <{header.name}>")
    writer.line("%}")

    writer.snippet("snippets_swig/prologue.i")
    writer.snippet("snippets_swig/cmd_director.i")

    writer.line("%pythoncode %{")
    writer.snippet("snippets_swig/iterators.py")
    writer.line("%}")

    for generic in generics.values():
        write_generic(writer, generic)

    for cls in classes.values():
        write_class(writer, cls)

    for director in directors.values():
        write_director(writer, director)

    for enum in enums:
        write_enum(writer, enum)

    for macro_enum in macro_enums:
        for name, definition in macro_enum.defines.items():
            writer.line(f"#define {name} {definition}")

    writer.line("%extend rz_cmd_t {")
    writer.snippet("snippets_swig/register_swig_command.cpp")  # TODO: %catches
    writer.line("}")

    writer.line("%extend rz_core_t {", "%pythoncode %{")
    writer.snippet("snippets_swig/register_command.py")
    writer.line("%}", "}")


class FuncKind(PyEnum):
    """
    Python enumeration for kind of class function
    """

    METHOD = 1
    STATIC = 2
    CONSTRUCTOR = 3
    DESTRUCTOR = 4
    GENERIC = 5


def write_generic(writer: Writer, generic: Generic) -> None:
    """
    Generate generic definition and specializations

    Generics are implemented with a macro definition
    which takes in a TYPE argument
    """
    writer.line(f"%define %{generic.name}(TYPE)")
    with writer.indent():
        writer.line(f"%nodefaultctor {generic.name}_##TYPE;")

        # The generic and its specializations are equal in C
        # eg. RzList_int == RzList
        writer.line("%{", f"typedef {generic.name} {generic.name}_##TYPE;", "%}")

        # Treat them differently in SWIG only
        writer.line(f"typedef struct {{}} {generic.name}_##TYPE;")

        writer.line(f"%extend {generic.name}_##TYPE {{")
        with writer.indent():
            for name, method in generic.methods.items():
                write_func(writer, method, name, FuncKind.GENERIC)

            for python_lines in generic.python_methods.values():
                writer.line("%pythoncode %{")
                with writer.indent():
                    writer.line(*python_lines)
                writer.line("%}")
        writer.line("}")
    writer.line("%enddef")

    for specialization in generic.specializations:
        writer.line(f"%{generic.name}({specialization})")

    for specialization, extension in generic.specialization_extensions.items():
        writer.line(f"%extend {generic.name}_{specialization} {{")
        with writer.indent():
            writer.line(*extension)
        writer.line("}")


def stringify_decl(expr: str, ctype: CType, generic: bool = False) -> str:
    """
    Get the spelling of a C declaration for a given name and type
    """

    pointing = False
    while True:
        if isinstance(ctype, CPrimitiveType):
            if ctype.type_.kind == TypeKind.BOOL:
                return f"bool {expr}"
            if generic and ctype.type_.kind == TypeKind.VOID:
                return f"TYPE {expr}"
            return f"{ctype.type_.spelling} {expr}"

        # type_.spelling automatically applies const
        # for other ctypes, do so manually
        if ctype.type_.is_const_qualified():
            expr = "const " + expr

        if isinstance(ctype, CPointerType):
            expr = "*" + expr
            ctype = ctype.pointee
            pointing = True
            continue

        if isinstance(ctype, CRecordType):
            if generic:
                return f"{generic_structs[ctype.decl_spelling].name}_##TYPE {expr}"
            if ctype.generic:
                return f"{ctype.generic.name}_{ctype.specialization} {expr}"
            return f"{class_structs[ctype.decl_spelling].name} {expr}"

        if isinstance(ctype, CTypedefType):
            if isinstance(ctype.canonical, CRecordType) and (
                generic or ctype.canonical.generic
            ):
                ctype = ctype.canonical
                continue
            return f"{ctype.cursor.spelling} {expr}"

        # Wrap in parentheses if the previous node
        # was a pointer (to fix precedence)
        if pointing:
            expr = f"({expr})"
            pointing = False

        if isinstance(ctype, CFunctionType):
            args = ", ".join([stringify_decl("", arg) for arg in ctype.args])
            expr = f"{expr}({args})"
            ctype = ctype.result
        elif isinstance(ctype, CArrayType):
            element_count = ctype.element_count or ""
            expr = f"{expr}[{element_count}]"
            ctype = ctype.element
        else:
            assert_never(ctype)


def write_class(writer: Writer, cls: Class) -> None:
    """
    Generate SWIG class
    """
    writer.line(
        f"typedef struct {cls.struct_name} {cls.name};",
        f"%rename {cls.struct_name} {cls.name};",
    )

    # %rename fields
    for field in cls.fields.values():
        if field.rename:
            writer.line(f"%rename {cls.struct_name}::{field.name} {field.rename};")

    # Main struct
    writer.line(f"struct {cls.struct_name} {{")
    with writer.indent():
        for field in cls.fields.values():
            decl = stringify_decl(field.name, field.ctype)
            writer.line(f"{decl};")
    writer.line("};")

    # un %rename fields
    for field in cls.fields.values():
        if field.rename:
            writer.line(f'%rename {cls.struct_name}::{field.name} "";')

    # Extension
    if len(cls.funcs) != 0 or len(cls.methods) != 0:
        writer.line(f"%extend {cls.struct_name} {{")
        with writer.indent():
            if cls.constructor:
                write_func(
                    writer, cls.constructor, cls.struct_name, FuncKind.CONSTRUCTOR
                )
            if cls.destructor:
                write_func(writer, cls.destructor, cls.struct_name, FuncKind.DESTRUCTOR)
            for name, func in cls.funcs.items():
                write_func(writer, func, name, FuncKind.STATIC)
            for name, method in cls.methods.items():
                write_func(writer, method, name, FuncKind.METHOD)

        writer.line("}")


def write_func(writer: Writer, func: Func, name: str, kind: FuncKind) -> None:
    """
    Generate SWIG function
    """
    # Activate typemaps
    for typemap in func.typemaps:
        typemap_args = ", ".join(f"{arg.type_} {arg.name}" for arg in typemap.args)
        writer.line(f"%{typemap.name}_activate({typemap_args})")

    decl = stringify_decl(
        name,
        func.cfunc.result_ctype,
        isinstance(func, GenericFunc) and func.generic_ret,
    )

    args_outer = []
    if kind in [FuncKind.METHOD, FuncKind.DESTRUCTOR, FuncKind.GENERIC]:
        args_inner = ["$self"]
        args = func.cfunc.args[1:]
    else:
        args_inner = []
        args = func.cfunc.args

    args_nonnull = []  # Used for nullability contract

    for arg in args:
        arg_name = arg.cursor.spelling
        if arg_name == "self":
            arg_name = "_self"

        arg_decl = stringify_decl(
            arg_name,
            arg.ctype,
            isinstance(func, GenericFunc) and arg.cursor.spelling in func.generic_args,
        )

        if arg.default:
            arg_decl += f" = {arg.default}"

        args_outer.append(arg_decl)
        args_inner.append(arg_name)

        if "RZ_NONNULL" in arg.attrs:
            args_nonnull.append(arg_name)

    args_outer_str = ", ".join(args_outer)
    args_inner_str = ", ".join(args_inner)

    # Nullability checking contract
    if args_nonnull:
        writer.line(f"%contract {name}({args_outer_str}) {{", "require:")
        with writer.indent():
            for contract_arg in args_nonnull:
                writer.line(f"{contract_arg} != NULL;")
        writer.line("}")

    if kind in [FuncKind.METHOD, FuncKind.GENERIC]:
        writer.line(f"{decl}({args_outer_str}) {{")
    elif kind == FuncKind.STATIC:
        writer.line(f"static {decl}({args_outer_str}) {{")
    elif kind == FuncKind.CONSTRUCTOR:
        writer.line(f"{name}({args_outer_str}) {{")
    elif kind == FuncKind.DESTRUCTOR:
        writer.line(f"~{name}({args_outer_str}) {{")

    with writer.indent():
        if "RZ_DEPRECATE" in func.cfunc.attrs:
            writer.line(
                f'rizin_try_warn_deprecate("{name}", "{func.cfunc.cursor.spelling}");'
            )

        if kind == FuncKind.GENERIC:
            typecast = stringify_decl(
                "",
                func.cfunc.result_ctype,
                isinstance(func, GenericFunc) and func.generic_ret,
            )
            writer.line(
                f"return ({typecast}){func.cfunc.cursor.spelling}({args_inner_str});"
            )
        else:
            writer.line(f"return {func.cfunc.cursor.spelling}({args_inner_str});")

    writer.line("}")

    # Deactivate typemaps
    for typemap in func.typemaps:
        typemap_args = ", ".join(f"{arg.type_} {arg.name}" for arg in typemap.args)
        writer.line(f"%{typemap.name}_deactivate({typemap_args})")


def write_director(writer: Writer, director: Director) -> None:
    """
    Generate SWIG director
    """
    writer.line(f'%feature("director") {director.name}Director;')

    # Director struct
    writer.line("%inline %{", f"struct {director.name}Director {{")
    with writer.indent():
        for name, func in director.funcs.items():
            decl = stringify_decl(name, func.result_ctype)
            args_outer_str = ", ".join(
                stringify_decl(arg.name, arg.ctype) for arg in func.args
            )
            writer.line(
                f"virtual {decl}({args_outer_str}) {{",
                f'    throw Swig::DirectorPureVirtualException("{name}");',
                "}",
            )

        # Virtual destructor
        writer.line(f"virtual ~{director.name}Director() {{}}")
    writer.line("};", "%}")

    # Global
    writer.line(
        "%{",
        f"static {director.name}Director *SWIG_{director.name}Director = NULL;",
        "%}",
    )

    # Funcs
    writer.line("%{")
    for name, func in director.funcs.items():
        decl = stringify_decl(f"SWIG_{director.name}_{name}", func.result_ctype)
        args_outer_str = ", ".join(
            stringify_decl(arg.name, arg.ctype) for arg in func.args
        )
        args_inner_str = ", ".join(arg.name for arg in func.args)
        writer.line(
            f"{decl}({args_outer_str}) {{",
            f"    return SWIG_{director.name}Director->{name}({args_inner_str});",
            "}",
        )
    writer.line("%}")

    # Builder struct
    writer.line("%inline %{", f"struct {director.name}Builder {{")
    with writer.indent():
        for func_name in director.funcs.keys():
            writer.line(f"bool enable_{func_name};")

        for field_name, field_ctype in director.fields.items():
            decl = stringify_decl(field_name, field_ctype)
            writer.line(f"{decl};")

        writer.line(f"{director.name} *build({director.name}Director *director) {{")
        with writer.indent():
            writer.line(
                f"SWIG_{director.name}Director = director;",
                f"{director.name} *result = ({director.name}*)calloc(1, sizeof({director.name}));",
            )
            for func_name in director.funcs.keys():
                writer.line(
                    f"if (this->enable_{func_name}) {{",
                    f"    result->{func_name} = SWIG_{director.name}_{func_name};",
                    "}",
                )

            for field_name in director.fields.keys():
                writer.line(f"result->{field_name} = this->{field_name};")

            writer.line("return result;")
        writer.line("}")
    writer.line("};", "%}")

    # Python helper
    writer.line("%pythoncode %{", f"def register_{director.name}(director_class):")
    with writer.indent():
        writer.line("fields = [")
        with writer.indent():
            for field_name in director.fields.keys():
                writer.line(f'"{field_name}",')
        writer.line("]")

        writer.line("funcs = [")
        with writer.indent():
            for func_name in director.funcs.keys():
                writer.line(f'"{func_name}",')
        writer.line("]")

        writer.line(
            f"builder = {director.name}Builder()",
            "class_vars = vars(director_class).keys()",
            "for field in fields:",
            "    if field in class_vars:",
            "        attr = getattr(director_class, field)",
            "        setattr(builder, field, attr)",
            "for func in funcs:",
            "    if func in class_vars:",
            '        setattr(builder, f"enable_{func}", True)',
            "director = director_class()",
            "return director, builder.build(director)",
        )
    writer.line("%}")


def write_enum(writer: Writer, enum: Enum) -> None:
    """
    Generate SWIG enum
    """
    writer.line("typedef enum {")
    with writer.indent():
        for name, value in enum.fields.items():
            writer.line(f"{name} = {value},")
    writer.line(f"}} {enum.typedef_name};")
