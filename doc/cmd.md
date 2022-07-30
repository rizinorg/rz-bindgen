# rz_cmd.h

## The RzCmd struct
An `RzCmd` struct controls the commands in a Rizin shell.
The main instance is available in the `rcmd` field of an `RzCore` struct.

## Adding new commands
### Withou helper
Rizin's new shell implementation allows registering commands on the fly.
Like `RzBinPlugin`s, this feature is exposed in the bindings using SWIG directors.

### Without helper
Once again, extend the director class, `CmdDirector`, and override the `run` function with a function that accepts an `RzCore`, and `int argc`, and a `char **argv` as arguments, and that returns a boolean.

```py
import rizin

class CustomCommand(rizin.CmdDirector):
    def run(self, core, argc, argv):
        print("hello from python")
	return True

core = rizin.RzCore()
```

Since there is a often need to register multiple commands, the directors are stored in a `std::unordered_map` and registered using a custom `register_swig_command` method available on an `RzCmd` instance.

```c
void register_swig_command(const char *str, CmdDirector *director, RzCmdDescHelp *help, RzCmdDescHelp *group_help = NULL)
```

The first argument is the name of the command, by which it is called in a Rizin shell.
If the `group_help` argument is supplied, a command group will be made `rz_cmd_desc_group_new`.
Otherwise, a standard command is made using `rz_cmd_desc_argv_new`.

The `RzCmdDescHelp` object can be constructed from the bindings.
For a group command, the only requirement is the `summary` field, which is a `char*`.
Be sure to disown the object, as it will be passed to C code.

```py
user_group_desc_help = rizin.RzCmdDescHelp()
user_group_desc_help.thisown = False
user_group_desc_help.summary = "A custom group for user-defined commands"

core.rcmd.register_swig_command("u", None, None, user_group_desc_help)
```

For a standard command, the only requirement is the `args` field, which is an `RzCmdDescArg*`, terminated by a null `RzCmdDescArg`.
Each arg must have a name, which is a `char*`, and a type, which is an item in the `RzCmdArgType` enum.

To construct the args array, the bindings provide a helper `Array_RzCmdDescArg` class.
The constructor accepts the length of the array, and it is subscriptable from Python, allowing for setting of the contents.
Be sure to disown the `RzCmdDescHelp` object, as well as the `Array_RzCmdDescArg` object and the individual `RzCmdDescArg` objects.
To convert the array into an `RzCmdDescArg` pointer, use the `cast` method on it.

```py
custom_desc_help = rizin.RzCmdDescHelp()
custom_desc_help.thisown = False

custom_args = rizin.Array_RzCmdDescArg(1)
custom_args.thisown = False
null_arg = rizin.RzCmdDescArg()
null_arg.thisown = False
custom_args[0] = null_arg

custom_desc_help.args = custom_args.cast()
```

Finally, construct the class and register it using the `RzCmdDescHelp`s.
Once again, disown the object as it will be managed by C.
```py
custom_cmd = CustomCommand()
custom_cmd.__disown__()

core.rcmd.register_swig_command("uh", custom_cmd, custom_desc_help)
```

For the completed example, see `examples/4a-rz_cmd.md`.
Here's a sample run:
```
[0x00000000]> u?
Usage: u<h>   # A custom group for user-defined commands
| uh
[0x00000000]> uh
hello from python
[0x00000000]>
```

### With helper
The Python bindings provide the `register_group` and `register_command` helper methods on `RzCore` to make the process easier.

`register_group` takes the group name as the first argument and the group summary as the second argument.

`register_command` takes the command name as the first argument and a function as the second argument. It uses the Python `inspect` module to extract arguments and type hints from the provided function, and automatically constructs an `RzCmdDescArg*`.

To recreate the example above, all that is necessary is:

```py
def say_hello():
    print("hello from python")
    return True
core.register_group("u", "A custom group for user-defined commands")
core.register_command("uh", say_hello)
```

The register command function will pass the `RzCore` only if the first argument is annotated with an `RzCore` type hint.

For the other arguments, the following annotations are supported:
```py
str                -> RZ_CMD_ARG_TYPE_STRING
RzNumArg           -> RZ_CMD_ARG_TYPE_RZNUM
int                -> RZ_CMD_ARG_TYPE_NUM
RzFilenameArg      -> RZ_CMD_ARG_TYPE_FILE
RzFlagItem         -> RZ_CMD_ARG_TYPE_FLAG
RzAnalysisFunction -> RZ_CMD_ARG_TYPE_FCN
```

`RzFilenameArg` and `RzNumArg` are `str` and `int` types respectively, but change the way the argument is handled in Rizin (eg. autocompletion).

Here's an example for printing basic information about a function:
```py
def print_function_info(fn: rizin.RzAnalysisFunction):
    print("name:", fn.name)
    print("number of xrefs from:", len(fn.get_xrefs_from()))
    print("number of xrefs to:", len(fn.get_xrefs_to()))
    return True
core.register_command("uf", print_function_info)
```

For the completed example, see `examples/4b-rz_cmd.md`.
Here's a sample run using the Rizin plugin:
```
$ rizin `which ls`
 -- In visual mode press 'c' to toggle the cursor mode. Use tab to navigate
[0x00408820]> aaa
[x] Analyze all flags starting with sym. and entry0 (aa)
[x] Analyze function calls
[x] Analyze len bytes of instructions for references
[x] Check for classes
[x] Analyze local variables and arguments
[x] Type matching analysis for all functions
[x] Applied 0 FLIRT signatures via sigdb
[x] Propagate noreturn information
[x] Use -AA or aaaa to perform additional experimental analysis.
[0x00408820]> uf?
Error while executing command: uf?
[0x00408820]> #!python examples/4b-rz_cmd.py
[0x00408820]> uf?
Usage: uf <fn>
[0x00408820]> uf
Wrong number of arguments passed to `uf`, see its help with `uf?`
[0x00408820]> uf sym.millerrabin
sym.millerrabin    sym.millerrabin2
[0x00408820]> uf sym.millerrabin
name: sym.millerrabin
number of xrefs from: 2
number of xrefs to: 3
[0x00408820]>
```
