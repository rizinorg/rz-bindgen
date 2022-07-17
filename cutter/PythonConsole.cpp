// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#define CUTTER_ENABLE_PYTHON
#include <PythonManager.h>

#include "PythonConsole.h"
#include "PythonConsoleWriter.h"
#include "util.h"

#include <QScrollBar>
#include <iostream>

PythonConsole::PythonConsole(MainWindow *main) : CutterDockWidget(main) {
        ui.setupUi(this);

        PythonManager::ThreadHolder threadHolder;
        stdout = PyObj((PyObject *)PythonConsoleWriter_New("stdout", this));
        if (!stdout) {
                return;
        }

        stderr = PyObj((PyObject *)PythonConsoleWriter_New("stderr", this));
        if (!stderr) {
                return;
        }

        // Set up InteractiveInterpreter
        PyObj code_module(PyImport_ImportModule("code"));
        ABORT_IF(!code_module, "Could not import python code module");

        PyObj interpreter_ctor(PyObject_GetAttrString(
            code_module.get(), "InteractiveInterpreter"));
        ABORT_IF(!interpreter_ctor,
                 "Could not get InteractiveInterpreter object");

        interpreter = PyObj(PyObject_CallObject(interpreter_ctor.get(), NULL));
        ABORT_IF(!interpreter, "Could not construct InteractiveInterpreter");

        buffer = QStringList();

        connect(ui.inputLineEdit, &QLineEdit::returnPressed, this, [this]() {
                QString text = ui.inputLineEdit->text();
                buffer.append(text);

                QByteArray bytes = buffer.join("\n").toLocal8Bit();
                const char *input = bytes.data();

                PythonManager::ThreadHolder threadHolder;
                PyObj runsource(
                    PyObject_GetAttrString(interpreter.get(), "runsource"));
                ABORT_IF(!runsource,
                         "Could not get interpreter.runsource function");

                write(buffer.length() == 1 ? ">>> " : "... ");
                writeLine(text);

                PyObj result(
                    PyObject_CallFunction(runsource.get(), "(s)", input));
                if (result.get() == Py_False) {
                        buffer.clear();
                }

                ui.inputLineEdit->clear();
        });
}

void PythonConsole::write(QString str) {
        QScrollBar *scrollbar = ui.outputTextEdit->verticalScrollBar();
        bool scrollToBottom = scrollbar->value() == scrollbar->maximum();

        const QTextCursor cursor = ui.outputTextEdit->textCursor();
        ui.outputTextEdit->moveCursor(QTextCursor::End);
        ui.outputTextEdit->insertPlainText(str);
        ui.outputTextEdit->setTextCursor(cursor);

        if (scrollToBottom) {
                scrollbar->setValue(scrollbar->maximum());
        }
}

void PythonConsole::writeLine(QString str) {
        QScrollBar *scrollbar = ui.outputTextEdit->verticalScrollBar();
        bool scrollToBottom = scrollbar->value() == scrollbar->maximum();

        const QTextCursor cursor = ui.outputTextEdit->textCursor();
        ui.outputTextEdit->moveCursor(QTextCursor::End);
        ui.outputTextEdit->insertPlainText(str);
        ui.outputTextEdit->insertPlainText("\n");
        ui.outputTextEdit->setTextCursor(cursor);

        if (scrollToBottom) {
                scrollbar->setValue(scrollbar->maximum());
        }
}
