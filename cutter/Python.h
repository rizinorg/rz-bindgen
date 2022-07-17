// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifndef CUSTOM_PYTHON_H
#define CUSTOM_PYTHON_H

#pragma push_macro("slots")
#undef slots
#undef _GNU_SOURCE
#include <Python.h>
#pragma pop_macro("slots")

#define CUTTER_ENABLE_PYTHON
#include <PythonManager.h>

struct PyObjectDeleter {
        void operator()(PyObject *obj) {
                PythonManager::ThreadHolder threadHolder;
                Py_XDECREF(obj);
        }
};

#include <memory>
using PyObj = std::unique_ptr<PyObject, PyObjectDeleter>;

#endif
