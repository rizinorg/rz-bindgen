from typing import List, Optional
from enum import Enum

from clang.wrapper import CursorKind, Func

from module import rizin
from writer import BufferedWriter, DirectWriter


class FuncKind(Enum):
    CONSTRUCTOR = 0
    DESTRUCTOR = 1
    THIS = 2
    STATIC = 3


class ModuleFunc:
    writer: BufferedWriter
    contract: BufferedWriter

    def __init__(
        self,
        func: Func,
        kind: FuncKind,
        *,
        name: Optional[str] = None,
        generic_ret: bool = False,
        generic_args: Optional[List[str]] = None,
    ):
        writer = BufferedWriter()
        self.writer = writer

        ### Args ###
        # Ignore first argument for certain types
        args = list(func.get_arguments())
        if kind in [FuncKind.DESTRUCTOR, FuncKind.THIS]:
            args = args[1:]

        if generic_args is None:
            generic_args = []

        args_outer = []
        args_inner = []
        for arg in args:
            assert arg.kind == CursorKind.PARM_DECL
            args_inner.append(arg.spelling)
            args_outer.append(
                rizin.stringify_decl(
                    arg, arg.type, generic=(arg.spelling in generic_args)
                )
            )

        for generic_arg in generic_args:
            assert generic_arg in args_inner, "nonexistent generic argument specified"

        if kind == FuncKind.CONSTRUCTOR:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(args_inner)
            writer.line(f"{name}({args_outer_str}) {{")
        elif kind == FuncKind.DESTRUCTOR:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(["$self"] + args_inner)
            writer.line(f"~{name}({args_outer_str}) {{")
        elif kind == FuncKind.THIS:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(["$self"] + args_inner)
            decl = rizin.stringify_decl(
                func, func.result_type, name=name, generic=generic_ret
            )
            writer.line(f"{decl}({args_outer_str}) {{")
        elif kind == FuncKind.STATIC:
            args_outer_str = ", ".join(args_outer)
            args_inner_str = ", ".join(args_inner)
            decl = rizin.stringify_decl(
                func, func.result_type, name=name, generic=generic_ret
            )
            writer.line(f"static {decl}({args_outer_str}) {{")

        with writer.indent():
            if "RZ_DEPRECATE" in func.attrs:
                writer.line("if (rizin_warn_deprecate) {")
                with writer.indent():
                    writer.line(
                        f'puts("Warning: `{name}` calls deprecated function `{func.spelling}`");'
                    )
                    writer.line("if (rizin_warn_deprecate_instructions) {")
                    with writer.indent():
                        writer.line(
                            'puts("To disable this warning, set rizin_warn_deprecate to false");',
                            'puts("The method depends on the language being used");',
                            'puts("For python ");',
                        )
                    writer.line("}")
                writer.line("}")
            writer.line(f"return {func.spelling}({args_inner_str});")
        writer.line("}")

        ### Contracts ###
        contract = BufferedWriter()
        self.contract = contract

        args_nonnull = []

        for arg in args:
            if "RZ_NONNULL" in arg.attrs:
                args_nonnull.append(arg.spelling)

        if args_nonnull:
            contract.line(f"%contract {name}({args_outer_str}) {{", "require:")
            with contract.indent():
                for contract_arg in args_nonnull:
                    contract.line(f"{contract_arg} != NULL;")
            contract.line("}")

    def merge(self, writer: DirectWriter) -> None:
        writer.merge(self.contract)
        writer.merge(self.writer)
