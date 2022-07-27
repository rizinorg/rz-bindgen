"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

import rizin
from sys import argv

filename = argv[1]

core = rizin.RzCore()
core.file_open_load(filename)
# rz-bindgen defaults addr = 0, perms = 0, write_mode = 0
# for `rz_core_file_open_load` specifically

# Info logging
print(f"Loaded {core.files.length()} file(s)")
binfiles = core.files.first().binfiles  # or: core.file_cur().binfiles
print(f"First file has {binfiles.length()} binfile(s) named {binfiles.head().file}")

while True:
    core.flush(input("> "))
