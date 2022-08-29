"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""
from typing import List, Dict, Set, TypedDict, Optional, cast

import os
import json
import shlex
from argparse import ArgumentParser
from dataclasses import dataclass
from itertools import zip_longest

from clang.cindex import (
    Config,
    TranslationUnit,
    Cursor,
    CursorKind,
    SourceRange,
    SourceLocation,
)


messages = set()


def warn(message: str) -> None:
    """
    Print a warning only once
    """
    if message not in messages:
        print(message)
        messages.add(message)


def cursor_get_location(cursor: Cursor) -> str:
    """
    Get filename:line for a cursor location
    """
    location = cursor.location
    return f"in line {location.line} of file {os.path.abspath(location.file.name)}"


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


def cursor_get_comment(cursor: Cursor) -> Optional[str]:
    """
    Get /*<type>*/ comment on a cursor
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

    # Reconstruct SourceLocation
    start, end, translation_unit = (
        typeref.extent.end,
        cursor.location,
        cursor.translation_unit,
    )
    start = SourceLocation.from_position(
        translation_unit, start.file, start.line, start.column
    )
    end = SourceLocation.from_position(translation_unit, end.file, end.line, end.column)
    src_range = SourceRange.from_locations(start, end)

    # Ensure comment token exists
    try:
        token = next(cursor.translation_unit.get_tokens(extent=src_range))
    except StopIteration:
        if typeref_spelling in generic_types:
            warn(
                f"Missing type comment at {cursor_get_location(cursor)} "
                f"for {typeref_spelling}"
            )
        return None

    # Filter out other tokens
    comment = token.spelling
    if not comment.startswith("/*") or not comment.endswith("*/"):
        if typeref_spelling in generic_types:
            warn(
                f"Missing type comment at {cursor_get_location(cursor)} (token is not a comment)"
            )
        return None
    comment = comment[2:-2]

    if not comment.startswith("<") or not comment.endswith(">"):
        if typeref_spelling in generic_types:
            warn(f"Type comment at {cursor_get_location(cursor)} lacks angle bracks")
        return comment

    # Check pointer (or lack of) and space between pointer
    if typeref_spelling in {"RzList", "RzListIter", "RzPVector", "RzGraph"}:
        if comment[-2] != "*":
            warn(f"Type comment at {cursor_get_location(cursor)} lacks pointer")
        elif comment[-3] != " ":
            warn(
                f"Type comment at {cursor_get_location(cursor)} lacks space between pointer"
            )
    elif typeref_spelling in {"RzVector"}:
        if comment[-2] == "*":
            warn(
                f"Type comment at {cursor_get_location(cursor)} should not have pointer"
            )
    elif typeref_spelling in {"HtPP", "HtUP", "HtUU", "RBTree", "SdbList"}:
        pass
    else:
        warn(
            f"Type comment at {cursor_get_location(cursor)} for unknown type {typeref_spelling}"
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
        self.location = cursor_get_location(cursor)

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
            for field in cursor.get_children():
                if field.kind == CursorKind.FIELD_DECL:
                    cursor_get_comment(field)
                elif field.kind not in [CursorKind.STRUCT_DECL, CursorKind.UNION_DECL]:
                    warn(f"Unknown field cursor kind: {field.kind}")


class Command(TypedDict):
    """
    A single entry in compile_commands.json
    """

    file: str
    directory: str
    command: str


def main() -> None:
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

            check_translation_unit(
                TranslationUnit.from_source(abspath, clang_args),
                skipped_paths=skipped_paths,
                rizin_path=rizin_path,
            )


if __name__ == "__main__":
    main()
