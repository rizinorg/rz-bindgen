# rz_core.h

## The RzCore struct
An `RzCore` struct contains all the necessary data for a Rizin program, such as files and plugins.
It also contains `RzBin`, `RzAnalysis`, `RzIO`, and many other important structs

To create/destroy a core struct in C, use
```c
RZ_API RzCore *rz_core_new(void);
RZ_API void rz_core_free(RzCore *core);
```
In SWIG, these are mapped to the `RzCore` class constructor and destructor.

### RzCore Functions
rz_core.h contains many functions which operate on an `RzCore`, including:

#### rz_core_cmd
```c
RZ_API int rz_core_cmd(RzCore *core, const char *cmd, int log);
```
Runs a rizin command, as if it were typed into a rizin shell.
There are several variations, including:
- `rz_core_cmd0` - defaults `log` to 0
- `rz_core_cmdf` - accepts a format string and variadic args
- `rz_core_cmd_str` - returns the string instead of outputting it
- `rz_core_flush` - calls `rz_cons_flush()` afterwards

#### rz_core_file_open
```c
RZ_API RZ_BORROW RzCoreFile *rz_core_file_open(RZ_NONNULL RzCore *core, RZ_NONNULL const char *file, int flags, ut64 loadaddr);
```
Opens `file`
- `flags` is an `RZ_PERM_*` value (defined in `rz_types.h`). If `NULL`, open in readonly
- `loadaddr` is the base address

Most of the time, `rz_core_file_open_load` will be more convenient, as it also loads the binary:

#### rz_core_file_open_load
```c
RZ_API bool rz_core_file_open_load(RZ_NONNULL RzCore *core, RZ_NONNULL const char *filepath, ut64 addr, int perms, bool write_mode);
```
Opens `filepath` and loads bin info using `rz_core_bin_load`.
- `addr` is the base address. If `NULL`, use the file-provided baddr
- `perms` is an `RZ_PERM_*` value (defined in `rz_types.h`). If `NULL`, open in readonly
- `write_mode` makes the bin maps writable

## Example
We can use just these functions with python to create a rudimentary Rizin shell.
In the SWIG bindings, these functions are mapped to methods of RzCore.

```py
import rizin
from sys import argv

filename = argv[1]

core = rizin.RzCore()
core.file_open_load(filename)
# rz-bindgen defaults addr = 0, perms = 0, write_mode = 0
# for `rz_core_file_open_load` specifically

# Info logging
print(f"Loaded {len(core.files)} file(s)")
for i, corefile in enumerate(core.files):
    print(f"Corefile #{i + 1} has {len(corefile.binfiles)} binfile(s)")
    for binfile in corefile.binfiles:
        print(f" * {binfile.file}")

while True:
    core.flush(input("rizin> "))
```

Here's an example session:
```
Loaded 1 file(s)
Corefile #1 has 1 binfile(s)
 * dotnet20.exe
rizin> afl
rizin> aaa
[x] Analyze all flags starting with sym. and entry0 (aa)
[x] Analyze function calls
[x] Analyze len bytes of instructions for references
[x] Check for classes
[x] Analyze local variables and arguments
[x] Type matching analysis for all functions
[x] Applied 0 FLIRT signatures via sigdb
[x] Propagate noreturn information
[x] Use -AA or aaaa to perform additional experimental analysis.
> afl
0x0040233e    1 6            entry0
0x00402051    3 49   -> 16   sym.HelloWorld::Main
0x0040205f   99 24482 -> 31854 sym.HelloWorld::.ctor
```

### Plugins
When using the Rizin or Cutter Python plugins in the rz-bindgen repo, the `core` object on the `rizin` module is set to the existing `RzCore` instance, created by the system.
Otherwise, it is set to `None`.
