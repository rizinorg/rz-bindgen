## `prologue.i`
Sets up deprecation warning config variables and alert function.
Sets up typemap for buffer, len function arguments.
Defines `Array_String` array class.
Sets `core` to `None` for standalone Python scripts.

## `cmd_director.i`
Defines `CmdDirector` SWIG director class.
Defines `SWIGCmds` hashmap to store and look up directors.
Defines `SWIG_Cmd_run` function to use as an `RzCmd` callback.
Defines `rz_swig_cmd_desc_help_free` function to be called when deleting from the `SWIGCmds` hashmap.
Defines `Array_RzCmdDescArg` array class to define argument lists from SWIG.
Defines `RzNumArg` and `RzFilenameArg` empty Python classes for use in type annotations.

## `register_swig_command.cpp`
Defines `register_swig_command` helper function.
This is intended to be an extension onto `RzCmd`.

## `register_command.py`
Defines `register_group` and `register_command` Python helper functions.
This is intended to be a `%pythoncode` extension onto `RzCore`.

## `iterators.py`
Defines Python iterator classes for Rizin containers.
