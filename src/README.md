# Code structure

# Core
1. `main.py` is the entrypoint.
It parses args and sets up libclang before calling the binding specification file and appropriate binding generator(s).

2. `cparser_header.py` parses header files into libclang cursor wrapper nodes.
`cparser_types.py` contains wrappers for libclang types used during parsing. This is useful for exhaustive type checking.

3. `bindings.py` is the binding specification file. It calls the parser and arranges C functions and structs into classes and generics.

4. `generator_swig.py` and `generator_sphinx.py` are the backends for SWIG and Sphinx, respectively.
Also see `snippets_swig`, which holds longer snippets of code to be used in the SWIG generator.

# Binding
`binding_class.py` allows bindings to specify a class with fields, methods, and static functions.
`binding_func.py` contains function specification logic. It is not called directly by bindings, but instead through `binding_class` to specify methods and static functions.

`binding_enum.py` allows bindings to specify an enum or group of related `#define`s.

`binding_generic.py` allows bindings to specify a generic class with methods.
`binding_generic_specialization.py` is used to parse types and generate specializations for generics. It is factored out of binding_generic to fix a circular import.

`binding_director.py` allows bindings to specify a SWIG director class (to call guest language functions from rizin).

# Misc
`writer.py` contains helpers for writing lines and snippets to a file with indentation.

`lint.py` is ran on rizin source code for annotations (`RZ_*` macros and `/*<type>*/` comments)
