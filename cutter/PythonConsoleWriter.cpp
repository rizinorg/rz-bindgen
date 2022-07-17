// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#include "PythonConsoleWriter.h"

#include <iostream>

static PyMethodDef PyConsoleWriterMethods[] = {
    {"write",
     [](PyObject *self, PyObject *args) -> PyObject * {
             char *str;

             if (!PyArg_ParseTuple(args, "s", &str)) {
                     return NULL;
             }
             ((PythonConsoleWriter *)self)->console->write(str);

             Py_RETURN_NONE;
     },
     METH_VARARGS, "write"},
    {NULL}};

static PyTypeObject PythonConsoleWriterType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "python_console_stdout",
    .tp_basicsize = sizeof(PythonConsoleWriter),
    .tp_itemsize = 0,
    .tp_dealloc =
        [](PyObject *self) {
                PythonConsoleWriter *writer = (PythonConsoleWriter *)self;
                if (PySys_SetObject(writer->name, writer->old_writer) < 0) {
                        std::cout << "Could not restore sys." << writer->name
                                  << std::endl;
                        return;
                }
        },
    .tp_methods = PyConsoleWriterMethods,
};

PythonConsoleWriter *PythonConsoleWriter_New(const char *name,
                                             PythonConsole *console) {
        if (PyType_Ready(&PythonConsoleWriterType) < 0) {
                std::cout << "Could not ready PythonConsoleWriterType"
                          << std::endl;
                return nullptr;
        }

        PythonConsoleWriter *writer =
            PyObject_New(PythonConsoleWriter, &PythonConsoleWriterType);
        PyObj py_writer((PyObject *)writer);

        if (!py_writer) {
                std::cout << "Could not create " << name << " object"
                          << std::endl;
                return nullptr;
        }
        writer->console = console;
        writer->name = name;
        writer->old_writer = PySys_GetObject(name);

        if (!writer->old_writer) {
                std::cout << "Could not store old sys." << name << std::endl;
                return nullptr;
        }

        if (PySys_SetObject(name, py_writer.get()) < 0) {
                std::cout << "Could not set sys." << name << std::endl;
                return nullptr;
        }

        return writer;
}
