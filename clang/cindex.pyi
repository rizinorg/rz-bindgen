from clang.wrapper import RootCursor, Token, SourceLocation

from typing import List, Tuple, Iterator, Optional

class Diagnostic:
    spelling: str

class Index:
    pass

class SourceRange:
    @staticmethod
    def from_locations(start: SourceLocation, end: SourceLocation) -> SourceRange:
        pass
    start: SourceLocation
    end: SourceLocation

class TranslationUnit:
    @classmethod
    def from_source(
        cls,
        filename: str,
        args: Optional[List[str]] = None,
        unsaved_files: Optional[List[Tuple[str, str]]] = None,
        options: Optional[int] = None,
        index: Optional[Index] = None,
    ) -> TranslationUnit:
        pass
    def get_tokens(self, *, extent: SourceRange) -> Iterator[Token]:
        pass
    # Options
    PARSE_DETAILED_PROCESSING_RECORD: int

    # Properties
    diagnostics: List[Diagnostic]
    cursor: RootCursor

class Config:
    @staticmethod
    def set_library_path(path: str) -> None:
        pass
