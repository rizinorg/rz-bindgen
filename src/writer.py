"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only

Helpers for indentation
"""
from typing import List, Tuple, Iterator, TextIO

from contextlib import contextmanager


class DirectWriter:
    """
    Directly outputs to TextIO
    """

    _indent: int
    output: TextIO

    def __init__(self, output: TextIO):
        self._indent = 0
        self.output = output

    def line(self, *lines: str, extra_indents: int = 0) -> None:
        for line in lines:
            self.output.write("    " * (self._indent + extra_indents))
            self.output.write(line)
            self.output.write("\n")

    @contextmanager
    def indent(self) -> Iterator[None]:
        """
        Increases indentation level for duration of the context
        """
        self._indent += 1
        yield
        self._indent -= 1


class BufferedWriter:
    """
    Stores text in list of lines
    """

    _indent: int
    lines: List[Tuple[int, str]]

    def __init__(self) -> None:
        self._indent = 0
        self.lines = []

    def line(self, *lines: str) -> None:
        """
        Stores specified lines at the current indentation level
        """
        for line in lines:
            self.lines.append((self._indent, line))

    @contextmanager
    def indent(self) -> Iterator[None]:
        """
        Increases indentation level for duration of the context
        """
        self._indent += 1
        yield
        self._indent -= 1

    def write(self, writer: DirectWriter) -> None:
        """
        Writes self to DirectWriter
        """
        for indent, line in self.lines:
            writer.line(line, extra_indents=indent)
