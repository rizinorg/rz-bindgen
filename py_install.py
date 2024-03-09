#!/usr/bin/env python3
"""
SPDX-FileCopyrightText: 2024 kazarmy <kazarmy@gmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

import os
import shutil
import sys
import sysconfig

def install_files(scheme):
    for file in sys.argv[1:]:
        if file.endswith(".py"):
            dest_type = 'purelib'
        elif file.endswith(".so"):
            dest_type = 'platlib'
        install_dir = sysconfig.get_path(dest_type, scheme)
        shutil.copy(file, install_dir)
        print(f"Installing {os.path.basename(file)} to {install_dir}")

try:
    install_files(sysconfig.get_default_scheme())
except PermissionError:
    print("Installing to user site-packages since normal site-packages is not writeable")
    install_files(f"{os.name}_user")
