// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#include <Python.h>
#include <rz_core.h>
#include <rz_util/rz_file.h>
#include <swig_runtime.h>

static PyObject *rizin_module = NULL;

#define ABORT_IF(cond, ...)                                                    \
        if (cond) {                                                            \
                printf(__VA_ARGS__);                                           \
                result = false;                                                \
                goto done;                                                     \
        }

#define DEFER_SETUP                                                            \
        bool result = true;                                                    \
        int num_deferred = 0;                                                  \
        PyObject *deferred_pyobjs[32] = {0};

#define DEFER_DECREF(obj) deferred_pyobjs[num_deferred++] = obj

#define DEFER_CLEANUP                                                          \
        done:                                                                  \
        for (int i = 0; i < num_deferred; ++i) {                               \
                Py_XDECREF(deferred_pyobjs[i]);                                \
        }                                                                      \
        return result;

static int rz_bindings_run_file(RzLang *lang, const char *filename) {
        FILE *file = fopen(filename, "rb");
        return PyRun_SimpleFile(file, filename) == 0;
}

static int rz_bindings_init(RzLang *lang) {
        DEFER_SETUP;

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

        // Create core and add to rizin module
        rizin_module = DEFER_DECREF(PyImport_ImportModule("rizin"));
        ABORT_IF(!rizin_module, "Could not import rizin.py\n");

        swig_type_info *rz_core_type_info = SWIG_Python_TypeQuery("RzCore *");
        ABORT_IF(!rz_core_type_info, "Could not get RzCore* swig_type_info\n");

        PyObject *py_rz_core = DEFER_DECREF(
            SWIG_NewPointerObj(lang->user, rz_core_type_info, 0 /*own = 0*/));
        ABORT_IF(!py_rz_core, "Could not create RzCore* object\n");

        ABORT_IF(PyModule_AddObject(rizin_module, "core", py_rz_core) < 0,
                 "Could not add core to rizin module\n");

        Py_INCREF(py_rz_core);
        Py_INCREF(rizin_module);

        char *globpath = rz_file_path_join(bindings_dir, "*.py");
        RzList *files = rz_file_globsearch(globpath, 1);
        RzListIter *it;
        char *filename;

        rz_list_foreach(files, it, filename) {
                rz_bindings_run_file(lang, filename);
        }
        free(globpath);
        rz_list_free(files);

        DEFER_CLEANUP;
}

static int rz_bindings_fini(RzLang *lang) {
        Py_XDECREF(rizin_module);
        return Py_FinalizeEx() == 0;
}

static int rz_bindings_prompt(RzLang *lang) {
        DEFER_SETUP;

        // Create console
        PyObject *code_module = DEFER_DECREF(PyImport_ImportModule("code"));
        ABORT_IF(!code_module, "Could not import python code module\n");

        PyObject *console_ctor = DEFER_DECREF(
            PyObject_GetAttrString(code_module, "InteractiveConsole"));
        ABORT_IF(!console_ctor, "Could not get InteractiveConsole object\n");

        PyObject *console =
            DEFER_DECREF(PyObject_CallObject(console_ctor, NULL));
        ABORT_IF(!console, "Could not construct InteractiveConsole\n");

        // Import rizin
        PyObject *locals =
            DEFER_DECREF(PyObject_GetAttrString(console, "locals"));
        ABORT_IF(!locals, "Could not get console.locals dict\n");

        ABORT_IF(PyDict_SetItemString(locals, "rizin", rizin_module) > 0,
                 "Could not set console.locals\n");

        // Set up completer
        PyObject *readline_module =
            DEFER_DECREF(PyImport_ImportModule("readline"));
        ABORT_IF(!readline_module, "Could not import python readline module\n");

        PyObject *rlcompleter_module =
            DEFER_DECREF(PyImport_ImportModule("rlcompleter"));
        ABORT_IF(!rlcompleter_module,
                 "Could not import python rlcompleter module\n");

        PyObject *completer_ctor = DEFER_DECREF(
            PyObject_GetAttrString(rlcompleter_module, "Completer"));
        ABORT_IF(!completer_ctor, "Could not get Completer object\n");

        PyObject *completer = DEFER_DECREF(
            PyObject_CallFunctionObjArgs(completer_ctor, locals, NULL));
        ABORT_IF(!completer, "Could not construct Completer\n");

        PyObject *completer_complete =
            DEFER_DECREF(PyObject_GetAttrString(completer, "complete"));
        ABORT_IF(!completer_complete,
                 "Could not get completer.complete function\n");

        PyObject *set_completer = DEFER_DECREF(
            PyObject_GetAttrString(readline_module, "set_completer"));
        ABORT_IF(!set_completer,
                 "Could not get readline.set_completer function\n");

        PyObject *set_completer_res = DEFER_DECREF(PyObject_CallFunctionObjArgs(
            set_completer, completer_complete, NULL));
        ABORT_IF(!set_completer_res, "Could not call readline.set_completer\n");

        PyObject *parse_bind = DEFER_DECREF(
            PyObject_GetAttrString(readline_module, "parse_and_bind"));
        ABORT_IF(!parse_bind,
                 "Could not get readline.parse_and_bind function\n");

        PyObject *parse_bind_res = DEFER_DECREF(
            PyObject_CallFunction(parse_bind, "(s)", "tab: complete"));
        ABORT_IF(!parse_bind_res, "Could not call readline.parse_and_bind\n");

        // Run interact
        PyObject *interact =
            DEFER_DECREF(PyObject_GetAttrString(console, "interact"));
        ABORT_IF(!interact, "Could not get console.interact function\n");

        PyObject *interact_res =
            DEFER_DECREF(PyObject_CallObject(interact, NULL));
        ABORT_IF(!interact_res, "Could not call console.interact\n");

        DEFER_CLEANUP;
}

RzLangPlugin rz_lang_plugin_bindings = {
    .name = "python",
    .desc = "Python SWIG bindings",
    .license = "LGPL3",
    .ext = ".py",
    .init = rz_bindings_init,
    .prompt = rz_bindings_prompt,
    .run_file = rz_bindings_run_file,
    .fini = rz_bindings_fini,
};

RzLibStruct rizin_plugin = {
    .type = RZ_LIB_TYPE_LANG,
    .data = &rz_lang_plugin_bindings,
    .version = RZ_VERSION,
    .free = NULL,
};
