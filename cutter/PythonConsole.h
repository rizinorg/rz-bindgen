// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifndef PYTHON_CONSOLE_H
#define PYTHON_CONSOLE_H

#include "Python.h"
#include <widgets/CutterDockWidget.h>

#include "ui_PythonConsole.h"

class PythonConsole : public CutterDockWidget {
        Q_OBJECT

      private:
        Ui::PythonConsole ui;
        PyObj stdout;
        PyObj stderr;
        PyObj interpreter;

        QStringList buffer;

      public:
        PythonConsole(MainWindow *main);
        void write(QString str);
        void writeLine(QString str);
};

#endif
