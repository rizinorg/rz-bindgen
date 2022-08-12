"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""
from typing import List, Dict, TYPE_CHECKING

from clang.cindex import Cursor, CursorKind

from cparser_types import (
    CType,
    CPointerType,
    CRecordType,
    CFunctionType,
    CIncompleteArrayType,
    CFixedArrayType,
    CTypedefType,
    CPrimitiveType,
    assert_never,
)

if TYPE_CHECKING:
    from binding_generic import Generic

generic_structs: Dict[str, "Generic"] = {}


def gen_ctype_specializations(cursors: List[Cursor], ctype: CType) -> None:
    """
    Generates necessary specializations for a cursor and type

    Multiple cursors are provided as input to accomodate for typedefs
    which have their own type comments
    """
    if isinstance(ctype, CPointerType):
        gen_ctype_specializations(cursors, ctype.pointee)
    elif isinstance(ctype, CTypedefType):
        if not isinstance(ctype.canonical, CRecordType):
            gen_ctype_specializations(cursors + [ctype.cursor], ctype.canonical)
        else:
            gen_ctype_specializations(cursors, ctype.canonical)
    elif isinstance(ctype, CFunctionType):
        gen_ctype_specializations(cursors, ctype.result)
        cursor_args = [
            cursor
            for cursor in cursors[-1].get_children()
            if cursor.kind == CursorKind.PARM_DECL
        ]

        assert len(cursor_args) == len(ctype.args)
        arg_names = []
        for arg_cursor, arg_ctype in zip(cursor_args, ctype.args):
            gen_ctype_specializations([arg_cursor], arg_ctype)
            arg_names.append(arg_cursor.spelling)
        ctype.arg_names = arg_names
    elif isinstance(ctype, CRecordType):
        decl_spelling = ctype.decl_spelling
        if decl_spelling in generic_structs:
            ctype.generic = generic_structs[decl_spelling]

            for cursor in cursors:
                specialization = ctype.generic.add_specialization(cursor)
                if specialization:
                    ctype.specialization = specialization
                    break
            else:
                raise Exception(
                    "No /*<type>*/ comment found in cursors at "
                    + ", ".join(str(cursor.location) for cursor in cursors)
                )
    elif isinstance(ctype, CFixedArrayType):
        pass
    elif isinstance(ctype, CIncompleteArrayType):
        pass
    elif isinstance(ctype, CPrimitiveType):
        pass
    else:
        assert_never(ctype)
