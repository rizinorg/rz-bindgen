# The Rizin API

Rizin makes most of its functionality available in the C headers within `librz/include`. Within these headers, symbols marked with the `RZ_API` macro are exported for external use.

Rizin also uses several empty macros to mark header properties. These are:
- `RZ_NULLABLE` and `RZ_NONNULL` for nullability
- `RZ_OWN` and `RZ_BORROW` for ownership
- `RZ_DEPRECATE` for deprecation

## rz-bindgen
Rizin offers scripting support using a custom SWIG binding generator.
This tutorial focuses on the Python SWIG bindings, but will make note of the underlying C functions being used.
Many of the techniques will apply to the other SWIG languages, as well as the C API.

The most obvious transformation the generator performs is the introduction of classes.
Classes are always backed by a C struct, and almost all of the struct members will be available as instance variables of the class.

Functions which operate on structs will become methods of that class. This is usually determined by the prefix of the C function, as well as the first argument.
For example, `rz_core_file_open_load` starts with `rz_core_file` and takes an `RzCore *` as the first argument.

```py
import rizin

"""
Certain structs become constructable classes:
"""
# creates rz_core_t struct
core = rizin.RzCore() # calls rz_core_new()

"""
Functions with a certain prefix, and take a class as the first
argument become class methods
"""
# calls rz_core_file_open_load with `core` as the first argument
core.file_open_load("test.exe") # "test.exe" is the second argument
```

For structs which represent an entire header, such as `RzCons` for `rz_cons.h`, functions with an applicable prefix are mapped to static methods.
For example, the `rz_cons_` prefix is used to select static methods on `RzCons`.

```py
rizin.RzCons.flush() # calls rz_cons_flush
```
