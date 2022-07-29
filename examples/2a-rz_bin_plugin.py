"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

# This is an example designed to show the internal steps taken
# by the helper functions. To see the recommended way of doing
# things, see `4b-rz_cmd.py`

import rizin
import sys


import rizin

class CustomBinPlugin(rizin.RzBinPluginDirector):
    def __init__(self):
        super().__init__()
        self.__disown__()

    def load_buffer(self, bf, obj, buf, sdb):
        print("name: ", bf.file)
        print("size: ", bf.size)
        return True

# Construct the director
rizin.cvar.SWIGRzBinPluginDirector = CustomBinPlugin()

plugin = rizin.RzBinPlugin()
plugin.name = "SWIGCustom"
plugin.load_buffer = rizin.SWIG_RzBinPlugin_load_buffer

core = rizin.RzCore()
plugin.thisown = False
core.bin.plugins.append(plugin)

# Run rizin and load binary
core.bin.force_plugin(plugin.name)
core.file_open_load(sys.argv[1])

while True:
    core.flush(input("> "))
