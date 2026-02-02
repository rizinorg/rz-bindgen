"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

import rizin
from rizin import RZ_CORE_CMD_EXIT as CMD_EXIT
import sys


class CustomBinPlugin(rizin.RzBinPluginDirector):
    name = "CustomBinPlugin"

    def load_buffer(self, bf, obj, buf, sdb):
        print("name: ", bf.file)
        print("size: ", bf.size)
        return True


plugin, plugin_struct = rizin.register_RzBinPlugin(CustomBinPlugin)

core = rizin.RzCore()
plugin_struct.thisown = False
core.bin.plugins.append(plugin_struct)

# Run rizin and load binary
core.bin.force_plugin(plugin.name)
core.file_open_load(sys.argv[1])

while core.flush(input("rizin> ")) != CMD_EXIT:
    pass
