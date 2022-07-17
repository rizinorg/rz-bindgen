// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#include <iostream>

#define ABORT_IF(cond, msg)                                                    \
        if (cond) {                                                            \
                std::cout << msg << std::endl;                                 \
                return;                                                        \
        }
