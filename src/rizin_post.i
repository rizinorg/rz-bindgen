// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifdef SWIG_DIRECTORS_ENABLED
%catches(const char*) rz_cmd_t::register_swig_command;
%extend rz_cmd_t {
    void register_swig_command(const char *str, CmdDirector *director, RzCmdDescHelp *help, RzCmdDescHelp *group_help = NULL) {
        // Get parent RzCmdDesc
        int len = strlen(str);
        if (len == 0) {
            throw "Command cannot be empty";
        }

        RzCmdDesc *parent;
        if (len == 1) {
            parent = rz_cmd_get_root($self);
        } else {
            char *dup = strdup(str);
            dup[len - 1] = '\0';
            parent = (RzCmdDesc*) ht_pp_find($self->ht_cmds, dup, NULL);
            free(dup);
        }

        if (!parent) {
            throw "Could not get parent RzCmdDesc";
        }

        RzCmdDesc *prev = (RzCmdDesc*) ht_pp_find($self->ht_cmds, str, NULL);
        std::string cmd(str);
        if (prev) { // Update existing RzCmdDesc
            auto it = SWIGCmds.find(cmd);
            if (it == SWIGCmds.end()) {
                throw "Builtin command already bound";
            }

            if (it->second.first != prev) {
                throw "SWIG RzCmdDesc does not match the currently bound one";
            }

            if (group_help) {
                if (prev->type != RZ_CMD_DESC_TYPE_GROUP) {
                    throw "Cannot set group_help of a type argv command";
                }
                rz_swig_cmd_desc_help_free(prev->help);
                prev->help = group_help;
            } else {
                if (prev->type == RZ_CMD_DESC_TYPE_GROUP) {
                    throw "Type group command needs group_help";
                }
                rz_swig_cmd_desc_help_free(prev->help);
                prev->help = help;
            }
            
            delete it->second.second;
            it->second.second = director;
        } else { // Create new RzCmdDesc
            RzCmdDesc *result;
            if (group_help) {
                result = rz_cmd_desc_group_new($self, parent, str, &SWIG_Cmd_run, help, group_help);
            } else {
                result = rz_cmd_desc_argv_new($self, parent, str, &SWIG_Cmd_run, help);
            }

            if (!result) {
                throw "Could not create binding";
            }

            SWIGCmds[cmd] = std::make_pair(result, director);
        }
    }
}

%extend rz_core_t {
    %pythoncode %{
    def register_group(self, cmd, summary):
        help_desc = RzCmdDescHelp()
        help_desc.thisown = False
        help_desc.summary = summary
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
