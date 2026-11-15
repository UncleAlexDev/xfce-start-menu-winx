#define PY_SSIZE_T_CLEAN
#include <stdio.h>
#include <dlfcn.h>
#include <Python.h>
#include <pygobject.h>
#include <libxfce4panel/libxfce4panel.h>

#ifndef PY_LIB_NAME
#define PY_LIB_NAME "libpython3.13.so.1.0"
#endif

#ifndef PLUGIN_DIR
#define PLUGIN_DIR "/usr/share/xfce-start-menu"
#endif


static void start_menu_construct(XfcePanelPlugin *plugin) {

	dlopen(PY_LIB_NAME, RTLD_LAZY | RTLD_GLOBAL);

    if (!Py_IsInitialized()) {
        Py_Initialize();
    }
    pygobject_init(-1, -1, -1);
    if (PyErr_Occurred()) {
        PyErr_Print();
        return;
    }

	PyRun_SimpleString("import sys; sys.path.insert(0, '" PLUGIN_DIR "')");

    PyObject *pModule = PyImport_ImportModule("start-menu-sys");
    if (pModule != NULL) {
        PyObject *pFunc = PyObject_GetAttrString(pModule, "setup_plugin");
        if (pFunc && PyCallable_Check(pFunc)) {
            PyObject *pPluginObj = pygobject_new(G_OBJECT(plugin));
            PyObject *pArgs = PyTuple_Pack(1, pPluginObj);
            PyObject *pValue = PyObject_CallObject(pFunc, pArgs);
            if (!pValue) {
                PyErr_Print();
            }
            Py_XDECREF(pValue);
            Py_DECREF(pArgs);
            Py_DECREF(pPluginObj);
        } else {
            PyErr_Print();
        }
        Py_XDECREF(pFunc);
        Py_DECREF(pModule);
    } else {
        PyErr_Print();
    }
    fflush(stderr);
    fflush(stdout);
}

XFCE_PANEL_PLUGIN_REGISTER(start_menu_construct)
