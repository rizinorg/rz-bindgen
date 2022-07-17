// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifndef PYTHON_CONSOLE_WRITER_H
#define PYTHON_CONSOLE_WRITER_H

#include "Python.h"

#include "PythonConsole.h"

typedef struct {
        PyObject_HEAD const char *name;
        PythonConsole *console;
        PyObject *old_writer;
} PythonConsoleWriter;

PythonConsoleWriter *PythonConsoleWriter_New(const char *name,
                                             PythonConsole *console);

#endif
