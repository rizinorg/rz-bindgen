"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only

This is a Rizin linter script, intended for use in CI.
It parses the compile_commands.json created by meson,
then runs libclang on those files with the specified arguments.

It detects TYPEREF cursors in function parameters, function return types
and struct fields. If the TYPEREF spelling is one of the prespecified
generic types, expect a /*<type>*/ comment and emits a warning if none is found.

Certain generic types, such as RzList, must include a pointer in their comment.
This is since many RzList specializations are for char*, pointing to a string's starting
character, and eliding the pointer would result in an RzList /*<char>*/, which loses
the implied meaning of holding a string.

Other generic types, such as RzVector, should not contain a pointer (RzPVector
should be used in cases where something must be pointed to).

The linter also enforces consistency in type comments between function declarations
and definitions. It also does this for Rizin annotations, such as RZ_OWN. This works
by defining the RZ_BINDINGS preprocessor flag, which sets the annotations to expand to
__attribute__((annotate)), which can be picked up by libclang.
"""
from typing import List, Dict, Set, TypedDict, Optional, cast

import os
import sys
import json
import shlex
from argparse import ArgumentParser
from dataclasses import dataclass
from itertools import zip_longest

from clang.cindex import (
    Config,
    TranslationUnit,
    TranslationUnitLoadError,
    Cursor,
    CursorKind,
    SourceRange,
    SourceLocation,
)


warnings = set()


def warn(warning: str) -> None:
    """
    Print a warning only once
    """
    if warning not in warnings:
        print(warning)
        warnings.add(warning)


def stringify_location(location: SourceLocation) -> str:
    """
    Get <relpath:filename:line> for a SourceLocation
    """
    path = os.path.relpath(os.path.abspath(location.file.name))
    return f"<{path}:{location.line}:{location.column}>"


def cursor_get_annotations(cursor: Cursor) -> List[str]:
    """
    Get RZ_* annotation attributes on a cursor
    """
    return [
        child.spelling
        for child in cursor.get_children()
        if child.kind == CursorKind.ANNOTATE_ATTR and child.location in cursor.extent
    ]


generic_types = {"RzList", "RzListIter", "RzPVector", "RzVector", "RzGraph"}


def cursor_get_comment(cursor: Cursor, *, packed: bool = False) -> Optional[str]:
    """
    Get /*<type>*/ comment on a cursor

    The packed argument is used to mark a struct field is marked by
    the RZ_PACK macro, so that the /*<type>*/ comment is searched for
    at the original location within the macro call
    """

    assert cursor.kind in [
        CursorKind.FUNCTION_DECL,
        CursorKind.PARM_DECL,
        CursorKind.FIELD_DECL,
    ]

    try:
        typeref = next(
            child
            for child in cursor.get_children()
            if child.kind == CursorKind.TYPE_REF
        )
        typeref_spelling = typeref.spelling
    except StopIteration:
        return None

    if packed:
        assert cursor.kind == CursorKind.FIELD_DECL
        src_range = SourceRange.from_locations(typeref.extent.end, cursor.location)
    else:
        # Reconstruct SourceLocation without macro bit
        start, end, translation_unit = (
            typeref.extent.end,
            cursor.location,
            cursor.translation_unit,
        )
        start = SourceLocation.from_position(
            translation_unit, start.file, start.line, start.column
        )
        end = SourceLocation.from_position(
            translation_unit, end.file, end.line, end.column
        )
        src_range = SourceRange.from_locations(start, end)

    # Ensure comment token exists
    try:
        token = next(cursor.translation_unit.get_tokens(extent=src_range))
    except StopIteration:
        if typeref_spelling in generic_types:
            warn(
                f"Missing type comment at {stringify_location(cursor.location)} "
                f"for {typeref_spelling}"
            )
        return None

    # Filter out other tokens
    comment = token.spelling
    if not comment.startswith("/*") or not comment.endswith("*/"):
        if typeref_spelling in generic_types:
            warn(
                f"Missing type comment at {stringify_location(cursor.location)} "
                "(token is not a comment)"
            )
        return None
    comment = comment[2:-2]

    if not comment.startswith("<") or not comment.endswith(">"):
        if typeref_spelling in generic_types:
            warn(
                f"Type comment at {stringify_location(cursor.location)} lacks angle brackets"
            )
        return comment

    # Check pointer (or lack of) and space between pointer
    if typeref_spelling in {"RzList", "RzListIter", "RzPVector", "RzGraph"}:
        if comment[-2] != "*":
            warn(f"Type comment at {stringify_location(cursor.location)} lacks pointer")
        elif comment[-3] != " ":
            warn(
                f"Type comment at {stringify_location(cursor.location)} lacks space between pointer"
            )
    elif typeref_spelling in {"RzVector"}:
        if comment[-2] == "*":
            warn(
                f"Type comment at {stringify_location(cursor.location)} should not have pointer"
            )
    elif typeref_spelling in {"HtPP", "HtUP", "HtUU", "RBTree", "SdbList"}:
        pass
    else:
        warn(
            f"Type comment at {stringify_location(cursor.location)} "
            f"for unknown type {typeref_spelling}"
        )

    return comment


@dataclass
class Arg:
    """
    Groups an argument's annotations and comment
    """

    annotations: List[str]
    comment: Optional[str]


class Function:
    """
    Represents a libclang function cursor and facilitates diffing with other functions
    """

    name: str
    annotations: List[str]
    comment: Optional[str]
    args: List[Arg]
    location: str

    def __init__(self, cursor: Cursor):
        self.name = cursor.spelling
        self.location = stringify_location(cursor.location)

        self.annotations = cursor_get_annotations(cursor)
        self.comment = cursor_get_comment(cursor)

        self.args = [
            Arg(
                annotations=cursor_get_annotations(arg), comment=cursor_get_comment(arg)
            )
            for arg in cursor.get_arguments()
        ]

    def diff(self, new: "Function") -> None:
        """
        Compare annotations and comments on function return type and arguments.

        Warn if mismatch
        """

        for annotation, new_annotation in zip_longest(
            self.annotations, new.annotations, fillvalue=None
        ):
            if annotation != new_annotation:
                warn(
                    f"Mismatched function annotation for {new.name} "
                    f"at {new.location} : {new_annotation} "
                    f"(was {annotation} at {self.location}"
                )

        if self.comment != new.comment:
            warn(
                f"Mismatched function type comment for {new.name} "
                f"at {new.location} : {new.comment} "
                f"(was {self.comment} at {self.location})"
            )

        for arg, new_arg in zip_longest(self.args, new.args, fillvalue=None):
            assert arg and new_arg

            for annotation, new_annotation in zip_longest(
                arg.annotations, new_arg.annotations, fillvalue=None
            ):
                if annotation != new_annotation:
                    warn(
                        f"Mismatched function annotation for {new.name} "
                        f"at {new.location} : {new_annotation} "
                        f"(was {annotation} at {self.location}"
                    )

                if arg.comment != new_arg.comment:
                    warn(
                        f"Mismatched function argument type comment for {new.name} "
                        f"at {new.location} : {new.comment} "
                        f"(was {self.comment} at {self.location})"
                    )


def check_translation_unit(
    translation_unit: TranslationUnit, *, skipped_paths: Set[str], rizin_path: str
) -> None:
    """
    Check for issues in translation_unit
    """

    for diagnostic in translation_unit.diagnostics:
        warn(
            f"Translation unit diagnostic at "
            f"{stringify_location(diagnostic.location)}: {diagnostic.spelling}"
        )

    functions: Dict[str, Function] = {}

    for cursor in translation_unit.cursor.get_children():
        cursor_file = cursor.location.file
        if not cursor_file:
            continue

        abspath = os.path.abspath(cursor_file.name)
        if not abspath.startswith(rizin_path):
            continue

        if abspath in skipped_paths:
            continue

        if cursor.kind == CursorKind.FUNCTION_DECL:
            function = Function(cursor)

            if function.name in functions:
                function.diff(functions[function.name])
            functions[function.name] = function
        elif cursor.kind == CursorKind.STRUCT_DECL:
            packed = False
            for field in cursor.get_children():
                if field.kind == CursorKind.PACKED_ATTR:
                    packed = True
                elif field.kind == CursorKind.FIELD_DECL:
                    cursor_get_comment(field, packed=packed)
                elif field.kind not in [
                    CursorKind.STRUCT_DECL,
                    CursorKind.UNION_DECL,
                    CursorKind.ENUM_DECL,
                ]:
                    warn(f"Unknown field cursor kind: {field.kind}")


class Command(TypedDict):
    """
    A single entry in compile_commands.json
    """

    file: str
    directory: str
    command: str


def main() -> int:
    """
    CLI Entrypoint
    """
    parser = ArgumentParser()
    parser.add_argument("--clang-path", required=True)
    parser.add_argument("--clang-args", required=True)
    parser.add_argument("--rizin-path", required=True)
    args = parser.parse_args()

    Config.set_library_path(cast(str, args.clang_path))
    clang_base_args = shlex.split(cast(str, args.clang_args)) + ["-DRZ_BINDINGS"]
    rizin_path = os.path.abspath(cast(str, args.rizin_path))

    skipped_paths = {
        os.path.join(rizin_path, "librz", *segments)
        for segments in [
            ["include", "rz_list.h"],
            ["util", "list.c"],
            ["include", "rz_skiplist.h"],
            ["util", "skiplist.c"],
            ["include", "rz_vector.h"],
            ["util", "vector.c"],
            ["include", "rz_util", "rz_graph.h"],
            ["util", "graph.c"],
            ["include", "rz_util", "rz_idpool.h"],
            ["util", "idpool.c"],
            ["util", "regex", "regcomp.c"],
            ["include", "rz_magic.h"],
        ]
    }

    # Used to parse compile_commands command entry
    cmd_parser = ArgumentParser()
    cmd_parser.add_argument("-I", action="append")
    cmd_parser.add_argument("-D", action="append")

    with open(
        os.path.join(rizin_path, "build", "compile_commands.json"), encoding="utf-8"
    ) as compile_commands:
        commands: List[Command] = json.loads(compile_commands.read())

        for command in commands:
            abspath = os.path.abspath(
                os.path.join(command["directory"], command["file"])
            )
            relpath = os.path.relpath(abspath, rizin_path)

            if relpath.startswith("subproject") or relpath.startswith("test"):
                continue

            namespace, _ = cmd_parser.parse_known_args(shlex.split(command["command"]))
            defines = cast(List[str], namespace.D)
            includes = cast(List[str], namespace.I)

            clang_args = clang_base_args.copy()
            clang_args += ["-D" + define for define in defines]
            clang_args += [
                "-I" + os.path.join(command["directory"], include)
                for include in includes
            ]

            try:
                check_translation_unit(
                    TranslationUnit.from_source(abspath, clang_args),
                    skipped_paths=skipped_paths,
                    rizin_path=rizin_path,
                )
            except TranslationUnitLoadError:
                warn(f"Failed to parse file {relpath}")

    return len(warnings)


if __name__ == "__main__":
    sys.exit(main())
