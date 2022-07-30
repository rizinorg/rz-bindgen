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
print(f"Loaded {len(core.files)} file(s)")
for i, corefile in enumerate(core.files):
    print(f"Corefile #{i + 1} has {len(corefile.binfiles)} binfile(s)")
    for binfile in corefile.binfiles:
        print(f" * {binfile.file}")

while True:
    core.flush(input("rizin> "))
