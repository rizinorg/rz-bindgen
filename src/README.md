# Code structure

## `main.py`
Entrypoint.
First, parses args and sets up program.
Then, calls the binding specification file
Finally, calls appropriate binding generator(s) and writes output.

## `cparser_header.py`
Parses header files into libclang cursor wrapper nodes.

## `cparser_types.py`
Parses and wraps libclang types.
Useful for exhaustive type checking.

## `bindings.py`
Binding specification file.

## `generator_swig.py`
Generator backend for SWIG.
Also see `snippets_swig`, which holds longer snippets of code to be used in this generator.

## `generator_sphinx.py`
Generator backend for Python Sphinx documentation.

## `writer.py`
Helper class for writing lines and snippets to a file with indentation.

## Binding
### `binding_class.py`
Helpers to specify a class with fields, methods, and static functions.

### `binding_director.py`
Helpers to specify a SWIG director class.
This is used to call guest language functions from rizin.

### `binding_enum.py`
Helpers to specify an enum or group of `#define`s.

### `binding_func.py`
Helpers to specify functions.
Called from `binding_class` to specify methods and static functions.

### `binding_generic.py`
Helpers to specify a generic class with methods.

### `binding_generic_specialization.py`
Used to parse types and generate specializations for generics.
Factored out of binding_generic to fix a circular import.
