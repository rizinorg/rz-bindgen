"""
Helpers for indentation
"""
from typing import List, Tuple, Iterator, TextIO

from contextlib import contextmanager


class BufferedWriter:
    """
    Stores text in list of lines
    """

    _indent: int
    lines: List[Tuple[int, str]]

    def __init__(self) -> None:
        self._indent = 0
        self.lines = []

    def line(self, text: str) -> None:
        self.lines.append((self._indent, text))

    @contextmanager
    def indent(self) -> Iterator[None]:
        self._indent += 1
        yield
        self._indent -= 1


class DirectWriter:
    """
    Directly outputs to TextIO
    """

    _indent: int
    output: TextIO

    def __init__(self, output: TextIO):
        self._indent = 0
        self.output = output

    def line(self, text: str) -> None:
        self.output.write("    " * self._indent)
        self.output.write(text)
        self.output.write("\n")

    def merge(self, buffered_writer: BufferedWriter) -> None:
        for indent, text in buffered_writer.lines:
            self.output.write("    " * (indent + self._indent))
            self.output.write(text)
            self.output.write("\n")

    @contextmanager
    def indent(self) -> Iterator[None]:
        self._indent += 1
        yield
        self._indent -= 1
