// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#include <Python.h>
#include <rz_core.h>
#include <swig_runtime.h>

static PyObject *py_rz_core = NULL;

#define ABORT_IF(cond, ...)                                                    \
        if (cond) {                                                            \
                printf(__VA_ARGS__);                                           \
                result = false;                                                \
                goto done;                                                     \
        }

#define DEFER_DECREF(obj) deferred_pyobjs[num_deferred++] = obj

static bool rz_bindings_init(RzCore *core) {
        bool result = true;
        int num_deferred = 0;
        PyObject *deferred_pyobjs[32] = {0};

        Py_Initialize();

        // Update PYTHONPATH
        char *plugins_dir = rz_path_home_prefix(RZ_PLUGINS);
        char *bindings_dir =
            rz_str_newf("%s" RZ_SYS_DIR "bindings", plugins_dir);

        PyObject *sys = DEFER_DECREF(PyImport_ImportModule("sys"));
        ABORT_IF(!sys, "Could not get sys module\n");

        PyObject *sys_path = DEFER_DECREF(PyObject_GetAttrString(sys, "path"));
        ABORT_IF(!sys_path, "Could not get sys.path\n");

        PyObject *sys_path_append =
            DEFER_DECREF(PyObject_GetAttrString(sys_path, "append"));
        ABORT_IF(!sys_path_append, "Could not get sys.path.append\n");

        PyObject *sys_path_append_res = DEFER_DECREF(
            PyObject_CallFunction(sys_path_append, "(s)", bindings_dir));
        ABORT_IF(!sys_path_append_res, "Could not append to sys.path\n");

        // Add core to rizin module
        PyObject *rizin_module = DEFER_DECREF(PyImport_ImportModule("rizin"));
        ABORT_IF(!rizin_module, "Could not import rizin.py\n");

        swig_type_info *rz_core_type_info = SWIG_Python_TypeQuery("RzCore *");
        ABORT_IF(!rz_core_type_info, "Could not get RzCore* swig_type_info\n");

        py_rz_core = DEFER_DECREF(
            SWIG_NewPointerObj(core, rz_core_type_info, 0 /*own = 0*/));
        ABORT_IF(!py_rz_core, "Could not create RzCore* object\n");

        Py_INCREF(py_rz_core);
done:
        for (int i = 0; i < num_deferred; ++i) {
                Py_XDECREF(deferred_pyobjs[i]);
        }
        return result;
}

static bool rz_bindings_fini(RzCore *core) {
        Py_XDECREF(py_rz_core);

        return true;
}

RzCorePlugin rz_core_plugin_bindings = {
    .name = "bindings",
    .desc = "Python bindings",
    .license = "LGPL3",
    .author = "wingdeans",
    .version = NULL,
    .init = rz_bindings_init,
    .fini = rz_bindings_fini,
};

RzLibStruct rizin_plugin = {
    .type = RZ_LIB_TYPE_CORE,
    .data = &rz_core_plugin_bindings,
    .version = RZ_VERSION,
    .free = NULL,
    .pkgname = "rz-bindings",
};
