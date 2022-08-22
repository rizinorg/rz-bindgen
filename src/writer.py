"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import Iterator, TextIO

import os
from contextlib import contextmanager


class Writer:
    """
    Helper class for writing indented lines to an output
    """

    output: TextIO
    indent_level: int
    indent_amount: int

    def __init__(self, output: TextIO, *, indent_amount: int = 4):
        self.output = output
        self.indent_level = 0
        self.indent_amount = indent_amount

    def line(self, *lines: str) -> None:
        """
        Write lines at current indentation
        """
        for line in lines:
            indent = self.indent_amount * self.indent_level
            self.output.write(" " * indent)
            self.output.write(line)
            self.output.write("\n")

    @contextmanager
    def indent(self) -> Iterator[None]:
        """
        Increase indentation level for duration of context
        """
        self.indent_level += 1
        yield
        self.indent_level -= 1

    def snippet(self, path: str) -> None:
        """
        Write a snippet file at current indentation

        File searched from this file's directory
        """
        path_segments = path.split("/")
        filename = os.path.join(os.path.dirname(__file__), *path_segments)
        with open(filename, encoding="utf-8") as snippet:
            self.line(*snippet.read().splitlines())
