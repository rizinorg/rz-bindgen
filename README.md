# rz-bindgen

rz-bindgen parses Rizin header files using libclang to generate SWIG .i binding files

## Usage
Requirements:
- meson
- ninja

- python >= 3.7
- libclang
- SWIG

Meson options:
- `clang_path`: Directory containing libclang.so, can usually be found using `llvm-config --libdir`
- `clang_args`: Extra arguments to pass to libclang
- `rizin_inc_path`: Directory containing rizin header files

To link with a non-system version of rizin, prepend the install's `lib/pkgconfig` directory to `PKG_CONFIG_PATH`
