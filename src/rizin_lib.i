// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

%include <pybuffer.i>

%define %buffer_len_activate(TYPEMAP, SIZE)
%pybuffer_mutable_binary(unsigned char *buf, unsigned long long len);
%enddef

%define %buffer_len_deactivate(TYPEMAP, SIZE)
%typemap(in) (unsigned char *buf, unsigned long long len);
%enddef
