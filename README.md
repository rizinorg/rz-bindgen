# rz-bindgen

rz-bindgen parses Rizin header files using libclang to generate SWIG .i binding files

For information on code structure, see [src/README.md](src/README.md).

For usage information, see [the documentation](doc/README.md).

## Building python plugin
Requirements:
- rizin > 0.4.0 (needs commit [6b7ea38](https://github.com/rizinorg/rizin/commit/6b7ea389698818beebaa55425b05d966cf3d7117))

- meson
- ninja

- python >= 3.7
- libclang
- SWIG

Meson options:
- `clang_path`: Directory containing libclang.so
  - Defaults to result of `llvm-config --libdir` if found
  - Otherwise, use Xcode clang path on MacOS
  - Otherwise, use `clang.exe` directory on windows
  - Otherwise, use `/usr/lib`

- `clang_args`: Extra arguments to pass to libclang
  - Defaults to setting resource-dir to result of `clang -print-resource-dir`

- `rizin_include_path`: Directory containing rizin header files
  - Defaults to using rizin found in pkg-config and CMake
  - To customize pkg-config search, set `PKG_CONFIG_PATH`
  - To customize CMake search, set `CMAKE_PREFIX_PATH`

## Building the Cutter plugin
Additional Requirements:
- cmake
- cutter
- qt

Install the cutter plugin to `<CUTTER_PLUGIN_DIR>/native/`
Install the python plugin (`rizin.py`, `_rizin`) to `<CUTTER_PLUGIN_DIR>/native/bindings/`
