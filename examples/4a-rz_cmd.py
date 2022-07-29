"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

# This is an example designed to show the internal steps taken
# by the helper functions. To see the recommended way of doing
# things, see `4b-rz_cmd.py`

import rizin

core = rizin.RzCore()

class CustomCommand(rizin.CmdDirector):
    def run(self, core, argc, argv):
        print("hello from python")
        return True

# Group desc help
user_group_desc_help = rizin.RzCmdDescHelp()
user_group_desc_help.thisown = False
user_group_desc_help.summary = "A custom group for user-defined commands"
core.rcmd.register_swig_command("u", None, None, user_group_desc_help)

# Command desc help
custom_desc_help = rizin.RzCmdDescHelp()
custom_desc_help.thisown = False

custom_args = rizin.Array_RzCmdDescArg(1)
custom_args.thisown = False
null_arg = rizin.RzCmdDescArg()
null_arg.thisown = False
custom_args[0] = null_arg

custom_desc_help.args = custom_args.cast()

# Construct and set
custom_cmd = CustomCommand()
custom_cmd.__disown__()
core.rcmd.register_swig_command("uh", custom_cmd, custom_desc_help)

core.prompt_loop()
