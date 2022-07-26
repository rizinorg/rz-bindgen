// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

%include <pybuffer.i>

%define %buffer_len_activate(TYPEMAP, SIZE)
%pybuffer_mutable_binary(unsigned char *buf, unsigned long long len);
%enddef

%define %buffer_len_deactivate(TYPEMAP, SIZE)
%typemap(in) (unsigned char *buf, unsigned long long len);
%enddef

#ifdef SWIG_DIRECTORS_ENABLED
%feature("director") CmdDirector;
%inline %{
struct CmdDirector {
    virtual bool run(RzCore *core, int argc, const char **argv) {
        throw Swig::DirectorPureVirtualException("run");
    }
    CmdDirector() {};
    virtual ~CmdDirector() {};
};
%}

%{
#include <unordered_map>

static auto SWIGCmds = std::unordered_map<std::string, std::pair<RzCmdDesc*, CmdDirector*>>();

RzCmdStatus SWIG_Cmd_run(RzCore *core, int argc, const char **argv) {
    std::string cmd(argv[0]);
    bool result = SWIGCmds.at(cmd).second->run(core, argc, argv);
    return result ? RZ_CMD_STATUS_OK : RZ_CMD_STATUS_ERROR;
}
%}

%include <carrays.i>
%array_class(RzCmdDescArg, Array_RzCmdDescArg);
#endif // SWIG_DIRECTORS_ENABLED
