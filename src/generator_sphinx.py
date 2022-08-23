"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

from typing import (
    List,
    Dict,
    DefaultDict,
    Set,
    Tuple,
    Union,
    Optional,
    Iterator,
    TextIO,
)

import os
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from itertools import chain
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET

from clang.cindex import TypeKind

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
from binding_class import Class, classes, class_structs
from binding_func import Func

from writer import Writer

doxygen_path: Optional[str] = None

DoxygenElements = Dict[str, Element]


class DoxygenFiles(Dict[str, DoxygenElements]):
    """
    Dictionary wrapper for retrieving XML elements from a filename

    If a filename is missing, parse and store its elements

    If an element name is duplicated, the element is ignored completely
    """

    names: Set[str]

    def __init__(self) -> None:
        self.names = set()
        super().__init__()

    def __missing__(self, path: str) -> DoxygenElements:
        tree = ET.parse(path)

        nodes: DoxygenElements = {}
        for node in tree.findall(
            "./compounddef/sectiondef/memberdef[@kind='function']"
        ):
            name = node.findtext("name")
            assert name
            if name in self.names:
                if name in nodes:
                    del nodes[name]
            else:
                self.names.add(name)
                nodes[name] = node
                super().__setitem__(path, nodes)

        return nodes


@dataclass
class DoxygenFile:
    """
    Groups a Doxygen XML file's name, refid, and absolute path
    """

    name: str
    refid: str
    path: str


doxygen_files = DoxygenFiles()


class DoxygenFunctions:
    """
    Wrapper for retrieving function XML element from a name
    """

    # Maps functions to filepaths
    function_files: DefaultDict[str, List[DoxygenFile]]

    def __init__(self) -> None:
        self.function_files = DefaultDict(list)

    def __getitem__(self, name: str) -> Element:
        files = self.function_files[name]

        if len(files) == 0:
            raise Exception(f"Function {name} not found in any file")

        if len(files) > 1:
            files = [f for f in files if not f.name.endswith(".h")]
            self.function_files[name] = files
            assert (
                len(files) == 1
            ), f"Function {name} is found in multiple files: {files}"

        return doxygen_files[files[0].path][name]


doxygen_functions = DoxygenFunctions()


def doxygen_children(node: Element) -> Iterator[Union[str, Element]]:
    """
    Create Iterator over text and node children of an Element
    """

    if node.text:
        yield node.text

    for child in node:
        yield child
        if child.tail:
            yield child.tail


class SphinxWriter(Writer):
    """
    Extended Writer class with additional sphinx-specific helpers
    """

    header_level: int

    def __init__(self, output: TextIO):
        super().__init__(output, indent_amount=3)
        self.header_level = 0

    def header(self, line: str, punctuation: str, *, overline: bool = False) -> None:
        """
        Write a sphinx header containing the specified text,
        and using the punctuation character as an underline
        (or optionally overline)
        """
        punctuation_line = punctuation * len(line)
        if overline:
            self.line(punctuation_line)
        self.line(line)
        self.line(punctuation_line)

    def title(self, title: str) -> None:
        """
        Write a sphinx title
        """
        self.header(title, "*", overline=True)

    @contextmanager
    def directive(
        self, name: str, *args: str, options: Optional[List[Tuple[str, str]]] = None
    ) -> Iterator[None]:
        """
        Write a sphinx directive, with *args as arguments
        and options as options

        Also increases indentation for duration of context
        """
        if not args:
            self.line(f".. {name}::")
        else:
            self.line(f".. {name}:: {args[0]}")
            spacer = " " * (5 + len(name))
            for arg in args[1:]:
                self.line(f"{spacer} {arg}")

        self.indent_level += 1

        if options:
            for option_name, value in options:
                self.line(f":{option_name}: {value}")

        self.line("")
        yield

        self.indent_level -= 1
        self.line("")


def generate(output_dir: str) -> None:
    """
    Generate sphinx docs and write to sphinx/ directory
    """
    sphinx_dir = os.path.join(output_dir, "sphinx")

    with suppress(FileExistsError):
        os.mkdir(sphinx_dir)

    with open(os.path.join(sphinx_dir, "conf.py"), "w", encoding="utf-8") as output:
        writer = Writer(output)
        writer.line(
            "html_theme = 'furo'",
            "",
            "import shutil",
            "import os",
            "def setup(app):",
            "    shutil.copytree(",
            f"        os.path.join('{doxygen_path}', 'html'),",
            "        os.path.join(app.outdir, 'doxygen'),",
            "        dirs_exist_ok=True",
            "    )",
        )

    with open(os.path.join(sphinx_dir, "index.rst"), "w", encoding="utf-8") as output:
        writer = SphinxWriter(output)
        writer.title("Rizin Python Bindings")
        writer.line(
            ".. toctree::",
            "   classes",
        )

    if doxygen_path:
        tree = ET.parse(os.path.join(doxygen_path, "xml", "index.xml"))

        for filenode in tree.findall("./compound[@kind='file']"):
            refid = filenode.attrib["refid"]
            filename = filenode.findtext("name")
            assert filename

            for membernode in filenode.findall("./member"):
                name = membernode.findtext("name")
                kind = membernode.attrib["kind"]
                if kind == "function":
                    assert name
                    doxygen_functions.function_files[name].append(
                        DoxygenFile(
                            name=filename,
                            refid=refid,
                            path=os.path.join(doxygen_path, "xml", f"{refid}.xml"),
                        )
                    )

    generate_classes(sphinx_dir)


def generate_classes(sphinx_dir: str) -> None:
    """
    Generate sphinx classes docs

    Writes documentation for each class
    in sphinx_output/classes directory

    Writes each class doc file to the table of contents
    tree in classes.rst
    """
    with open(os.path.join(sphinx_dir, "classes.rst"), "w", encoding="utf-8") as output:
        writer = SphinxWriter(output)
        writer.title("Classes")

        with writer.directive("toctree"):
            for classname in sorted(classes):
                writer.line(f"classes/{classname}")

    classes_dir = os.path.join(sphinx_dir, "classes")
    with suppress(FileExistsError):
        os.mkdir(classes_dir)

    for name, cls in classes.items():
        with open(
            os.path.join(classes_dir, f"{name}.rst"), "w", encoding="utf-8"
        ) as output:
            write_class(SphinxWriter(output), cls)


def write_class(writer: SphinxWriter, cls: Class) -> None:
    """
    Generate sphinx class
    """
    writer.title(cls.name)

    with writer.directive("py:class", cls.name):
        for name, field in sorted(cls.fields.items()):
            with writer.directive(
                "py:property",
                field.rename or name,
                options=[("type", stringify_ctype(field.ctype))],
            ):
                pass

        def stringify_func(name: str, func: Func, method: bool = True) -> str:
            args = []
            for arg in func.cfunc.args[1:] if method else func.cfunc.args:
                arg_name = arg.cursor.spelling
                if arg_name == "self":
                    arg_name = "_self"
                args.append(f"{arg_name}: {stringify_ctype(arg.ctype)}")

            args_str = ", ".join(args)
            result = stringify_ctype(func.cfunc.result_ctype)
            return f"{name}({args_str}) -> {result}"

        for directive, func_dict in [
            ("py:staticmethod", cls.funcs),
            ("py:method", cls.methods),
        ]:
            for name, func in sorted(func_dict.items()):
                with writer.directive(directive, stringify_func(name, func)):
                    if "RZ_DEPRECATE" in func.cfunc.attrs:
                        with writer.directive("warning"):
                            writer.line(
                                f"Calls deprecated function ``{func.cfunc.cursor.spelling}``"
                            )

                    if doxygen_path:
                        write_doxygen_function(writer, func.cfunc.cursor.spelling)


doxygen_escape_table = str.maketrans({"*": "\\*", "_": "\\_"})


def stringify_doxygen_computeroutput(node: Element) -> str:
    """
    Parse doxygen <computeroutput> tag and
    convert to reST ``internal literal``
    """

    segments = ["``"]

    for child in doxygen_children(node):
        if isinstance(child, str):
            segments.append(child)
        elif child.tag == "ref":
            assert child.text
            segments.append(child.text)
        else:
            raise Exception(
                f"Unknown doxygen tag in child of computeroutput: {child.tag}"
            )

    segments.append("``")
    return "".join(segments)


def write_doxygen_parameterlist(writer: SphinxWriter, node: Element) -> None:
    """
    Generate sphinx :param: options from doxygen <parameterlist> element
    """

    kind = node.attrib["kind"]

    if kind == "param":
        for item in node.findall("./parameteritem"):
            names = item.findall("./parameternamelist/parametername")
            assert len(names) == 1
            name = names[0].text

            if name == "self":
                name = "_self"

            segments = []

            paras = item.findall("./parameterdescription/para")
            assert len(paras) == 1
            para = paras[0]

            for child in doxygen_children(para):
                if isinstance(child, str):
                    segments.append(child.translate(doxygen_escape_table))
                elif child.tag == "ref":
                    assert child.text
                    segments.append(child.text)
                elif child.tag == "computeroutput":
                    segments.append(stringify_doxygen_computeroutput(child))
                else:
                    raise Exception(
                        f"Unknown doxygen tag in child of parameterdescription/para: {child.tag}"
                    )

            contents = "".join(segments)
            writer.line(f":param {name}: {contents}")
    else:
        raise Exception(f"Unknown doxygen parameteritem kind {kind}")


def write_doxygen_simplesect(writer: SphinxWriter, node: Element) -> None:
    """
    Generate sphinx :return: options from doxygen <simplesect> element
    """

    kind = node.attrib["kind"]

    if kind == "return":
        segments = []

        paras = node.findall("para")
        assert len(paras) == 1
        para = paras[0]

        for child in doxygen_children(para):
            if isinstance(child, str):
                segments.append(child.translate(doxygen_escape_table))
            elif child.tag == "ref":
                assert child.text
                segments.append(child.text)
            elif child.tag == "computeroutput":
                segments.append(stringify_doxygen_computeroutput(child))
            else:
                raise Exception(
                    f"Unknown doxygen tag in child of simpleselect/para: {child.tag}"
                )

        contents = "".join(segments)
        writer.line(f":return: {contents}", "")

    elif kind == "see":
        pass
    else:
        raise Exception(f"Unknown doxygen simplesect kind {kind}")


def write_doxygen_function(writer: SphinxWriter, name: str) -> None:
    """
    Generate documentation for function from doxygen xml
    """
    element = doxygen_functions[name]

    doxygen_file = doxygen_functions.function_files[name][0]
    url_hash = element.attrib["id"][-33:]
    writer.line(
        f"Calls function ``{name}``",
        f"(defined in `{doxygen_file.name} <../doxygen/{doxygen_file.refid}.html#{url_hash}>`__)",
        "",
    )

    for paragraph in chain.from_iterable(
        element.findall(xpath)
        for xpath in ["./briefdescription/para", "./detaileddescription/para"]
    ):
        segments = []

        for node in doxygen_children(paragraph):
            if isinstance(node, str):
                segments.append(node.translate(doxygen_escape_table))
            elif node.tag == "computeroutput":
                segments.append(stringify_doxygen_computeroutput(node))

            elif node.tag in "itemizedlist":
                writer.line("".join(segments), "")  # Flush segments

                for item in node.findall("./listitem/para"):
                    segments = []
                    for child in doxygen_children(item):
                        assert isinstance(child, str)
                        segments.append(child.translate(doxygen_escape_table))
                    contents = "".join(segments)
                    writer.line(f"- {contents}")

                segments = []
            elif node.tag == "parameterlist":
                writer.line("".join(segments), "")  # Flush segments
                segments = []

                write_doxygen_parameterlist(writer, node)

            elif node.tag == "ref":
                assert node.text
                segments.append(node.text)

            elif node.tag == "simplesect":
                writer.line("".join(segments), "")  # Flush segments
                segments = []

                write_doxygen_simplesect(writer, node)
            elif node.tag == "ulink":
                url = node.attrib["url"]
                text = node.text
                assert text
                segments.append(f"`{text} <{url}>`__")
            else:
                raise Exception(f"Unknown doxygen tag in child of para: {node.tag}")

        writer.line("".join(segments), "")


def stringify_ctype(ctype: CType) -> str:
    """
    Translate a CType to a Python type annotation
    """

    inner = None
    levels = 0

    while True:
        if isinstance(ctype, CPointerType):
            ctype = ctype.pointee
        elif isinstance(ctype, CArrayType):
            ctype = ctype.element
        else:
            break

        kind = ctype.type_.kind
        if levels == 0:
            if kind == TypeKind.VOID:
                inner = "Any"
                break
            if kind in [TypeKind.SCHAR, TypeKind.CHAR_S]:
                inner = "str"
                break

        levels += 1

    def stringify_ctype_primitive(ctype: CType) -> str:
        if isinstance(ctype, CPrimitiveType):
            kind = ctype.type_.kind
            if kind == TypeKind.VOID:
                return "None"

            if kind == TypeKind.BOOL:
                return "bool"

            if kind in [TypeKind.FLOAT, TypeKind.DOUBLE]:
                return "float"

            return "int"

        if isinstance(ctype, CRecordType):
            if ctype.generic:
                return f"{ctype.generic.name}[{ctype.specialization}]"
            return class_structs[ctype.decl_spelling].name

        if isinstance(ctype, CTypedefType):
            if isinstance(ctype.canonical, CRecordType) and ctype.canonical.generic:
                return stringify_ctype(ctype.canonical)
            return ctype.cursor.spelling

        if isinstance(ctype, CFunctionType):
            result = stringify_ctype(ctype.result)
            args = ", ".join(stringify_ctype(arg) for arg in ctype.args)
            return f"CFunction[[{args}], {result}]"

        assert not isinstance(ctype, CPointerType) and not isinstance(ctype, CArrayType)
        assert_never(ctype)

    if not inner:
        inner = stringify_ctype_primitive(ctype)

    if levels == 1:
        levels = 0

    return ("Pointer[" * levels) + inner + ("]" * levels)
