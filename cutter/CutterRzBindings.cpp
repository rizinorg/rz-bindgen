// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#include "CutterRzBindings.h"
#include "PythonConsole.h"
#include "util.h"

#include <Cutter.h>
#include <MainWindow.h>

#include "Python.h"
#include <swig_runtime.h>

#include <QStandardPaths>
#include <iostream>

void CutterRzBindings::setupPlugin() {
        QString appdata_loc =
            QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
        ABORT_IF(appdata_loc.isEmpty(), "No writable data directory");

        QDir dir = QDir(appdata_loc);
        ABORT_IF(!dir.cd("plugins") || !dir.cd("native") || !dir.cd("bindings"),
                 "No plugins/native/bindings directory");

        std::cout << "Loading rizin.py from "
                  << dir.absolutePath().toStdString() << std::endl;

        PythonManager::ThreadHolder threadHolder;
        Python()->addPythonPath(dir.absolutePath().toLocal8Bit().data());

        PyObj rizin_module(PyImport_ImportModule("rizin"));
        ABORT_IF(!rizin_module, "Could not import rizin.py");

        swig_type_info *rz_core_type_info = SWIG_Python_TypeQuery("RzCore *");
        ABORT_IF(!rz_core_type_info, "Could not get RzCore* swig_type_info");

        RzCore *rz_core = RzCoreLocked(Core());
        ABORT_IF(!rz_core, "Could not get RzCore");

        PyObj py_rz_core(
            SWIG_NewPointerObj(rz_core, rz_core_type_info, 0 /*own = 0*/));
        ABORT_IF(!py_rz_core, "Could not create RzCore* object");

        PyObj cutter_module(PyImport_ImportModule("cutter"));
        ABORT_IF(!cutter_module, "Could not import cutter");

        ABORT_IF(PyModule_AddObject(cutter_module.get(), "core",
                                    py_rz_core.get()) < 0,
                 "Could not add core to cutter module");

        Py_INCREF(py_rz_core.get());
}

void CutterRzBindings::setupInterface(MainWindow *main) {
        PythonConsole *widget = new PythonConsole(main);
        main->addPluginDockWidget(widget);
}
