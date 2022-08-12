#pragma SWIG nowarn=451,473

// Deprecation warnings
%inline %{
bool rizin_warn_deprecate = true;
bool rizin_warn_deprecate_instructions = true;
%}

%{
void rizin_try_warn_deprecate(const char *name, const char *c_name) {
    if (rizin_warn_deprecate) {
        printf("Warning: `%s` calls deprecated function `%s`\n", name, c_name);
        if (rizin_warn_deprecate_instructions) {
            puts("To disable this warning, set rizin_warn_deprecate to false");
            puts("The way to do this depends on the SWIG language being used");
            puts("For python, do `rizin.cvar.rizin_warn_deprecate = False`");
        }
    }
}
%}

// Buffer typemaps
%include <pybuffer.i>

%define %buffer_len_activate(TYPE, SIZE)
%pybuffer_mutable_binary(TYPE, SIZE);
%enddef

%define %const_buffer_len_activate(TYPE, SIZE)
%pybuffer_binary(TYPE, SIZE);
%enddef

%define %buffer_len_deactivate(TYPE, SIZE)
%typemap(in) (TYPE, SIZE);
%enddef

%define %const_buffer_len_deactivate(TYPE, SIZE)
%typemap(in) (TYPE, SIZE);
%enddef

// CArrays
%include <carrays.i>
%inline %{
    typedef char* String;
%}
%array_class(String, Array_String);

// Python plugin
%pythoncode %{
    core = None
%}
