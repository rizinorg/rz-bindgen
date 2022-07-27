"""
SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
SPDX-License-Identifier: LGPL-3.0-only
"""

import rizin
import sys
import cle  # https://github.com/angr/cle


class RzBufferWrapper:
    def __init__(self, buf):
        self.buf = buf

    def seek(self, where):
        self.buf.seek(where, 0)

    def read(self, length=None):
        if length is None:
            cur = self.buf.seek(0, rizin.RZ_BUF_CUR)  # save pos
            end = self.buf.seek(0, rizin.RZ_BUF_END)
            length = end - cur
            self.buf.seek(cur, rizin.RZ_BUF_SET)  # restore pos
        b = bytearray(length)
        self.buf.read(b)
        return b


class CLEBinPlugin(rizin.RzBinPluginDirector):
    name = "CLESWIGPlugin"
    desc = "ELF Binary Loader using the Angr CLE library"
    author = "wingdeans"
    license = "LGPL3"

    def load_buffer(self, bf, obj, buf, sdb):
        try:
            loader = cle.Loader(RzBufferWrapper(buf))
        except Exception as e:
            print(e)
            return False
        self.loader = loader
        return True

    def baddr(self, bf):
        return self.loader.main_object.linked_base

    def symbols(self, bf):
        syms = rizin.RzList_RzBinSymbol()

        for sym in self.loader.main_object.symbols:
            binsym = rizin.RzBinSymbol()
            binsym.thisown = False
            binsym.name = sym.name
            binsym.type = rizin.RZ_BIN_TYPE_FUNC_STR
            binsym.paddr = sym.linked_addr
            binsym.vaddr = sym.rebased_addr
            binsym.size = sym.size
            syms.append(binsym)
        return syms

    def sections(self, bf):
        sections = rizin.RzList_RzBinSection()
        for section in self.loader.main_object.sections:
            binsection = rizin.RzBinSection()
            binsection.thisown = False
            binsection.name = section.name
            binsection.size = section.filesize
            binsection.vsize = section.memsize
            binsection.paddr = section.offset
            binsection.vaddr = section.vaddr
            sections.append(binsection)
        return sections

    def maps(self, bf):
        # virtual memory mappings
        maps = rizin.RzList_RzBinMap()
        for segment in self.loader.main_object.segments:
            binmap = rizin.RzBinMap()
            binmap.thisown = False
            binmap.perm = segment.flags  # must be readable
            binmap.paddr = segment.offset
            binmap.psize = segment.filesize
            binmap.vaddr = segment.vaddr
            binmap.vsize = segment.memsize
            maps.append(binmap)
        return maps

    def strings(self, bf):
        # rz_bin_file_strings
        # the last parameter enables searching for strings everywhere,
        # which we disable to limit to searching only in data sections
        return bf.strings(4, False)

    def info(self, bf):
        info = rizin.RzBinInfo()
        info.has_va = True  # has virtual addresses
        return info


plugin, plugin_struct = rizin.register_RzBinPlugin(CLEBinPlugin)

core = rizin.RzCore()
plugin_struct.thisown = False
core.bin.plugins.append(plugin_struct)

# Run rizin and load binary
core.bin.force_plugin(plugin.name)
core.file_open_load(sys.argv[1])

core.prompt_loop()
