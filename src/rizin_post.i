// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifdef SWIG_DIRECTORS_ENABLED
%extend rz_cmd_t {
    void register_swig_command(const char *str, CmdDirector *director, RzCmdDescHelp *help, RzCmdDescHelp *group_help = NULL) {
        int len = strlen(str);
        if (len == 0) {
            throw std::runtime_error("Command cannot be empty");
        }

        RzCmdDesc *parent;
        if (len == 1) {
            parent = rz_cmd_get_root($self);
        } else {
            char *dup = strdup(str);
            dup[len - 1] = '\0';
            parent = ht_pp_find($self->ht_cmds, dup, NULL);
            free(dup);
        }

        if (!parent) {
            throw std::runtime_error("Could not get parent RzCmdDesc");
        }

        // Remove previous command
        RzCmdDesc *prev = ht_pp_find($self->ht_cmds, str, NULL);
        std::string cmd(str);
        if (prev) {
            auto it = SWIGCmds.find(cmd);
            if (it == SWIGCmds.end()) {
                throw std::runtime_error("Builtin command already bound");
            }

            if (it->second.first != prev) {
                throw std::runtime_error("SWIG RzCmdDesc does not match the currently bound one");
            }

	    SWIGCmds.erase(cmd);
            rz_cmd_desc_remove($self, prev);
        }

        RzCmdDesc *result;
        if (group_help) {
            result = rz_cmd_desc_group_new($self, parent, str, &SWIG_Cmd_run, help, group_help);
        } else {
            result = rz_cmd_desc_argv_new($self, parent, str, &SWIG_Cmd_run, help);
        }

        if (!result) {
            throw std::runtime_error("Could not create binding");
        }

        SWIGCmds[cmd] = std::make_pair(result, director);
    }
}

%extend rz_core_t {
    %pythoncode %{
    def register_group(self, cmd):
        help_desc = RzCmdDescHelp()
        help_desc.thisown = False
        self.rcmd.register_swig_command(cmd, None, None, help_desc)

    def register_command(self, cmd, fn):
        args = Array_RzCmdDescArg(1)
        args.thisown = False
        arg = RzCmdDescArg()
        arg.thisown = False
        args[0] = arg

        help_desc = RzCmdDescHelp()
        help_desc.thisown = False
        help_desc.args = args.cast()

        class wrapper(CmdDirector):
            def run(self, core, argc, argv):
                return fn(core, argc, argv)

        director = wrapper()
        director.__disown__()
        self.rcmd.register_swig_command(cmd, director, help_desc)
    %}
}
#endif // SWIG_DIRECTORS_ENABLED
