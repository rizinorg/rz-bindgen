# RzBinPlugin

It is possible to completely change the behavior of Rizin's binary loader by implementing an RzBinPlugin. The SWIG bindings expose RzBinPlugin, and other plugins, by using SWIG directors, which are a means of allowing SWIG languages to extend C++ classes and override virtual methods.

## Without helper
To use a SWIG director for an `RzBinPlugin`, simply extend an `RzBinPluginDirector` instance and override the necessary functions. For example, in Python, it is also necessary to call the superclass initializer and disown the director, so that it does not get destroyed from Python:

```py
import rizin

class CustomBinPlugin(rizin.RzBinPluginDirector):
    def __init__(self):
        super().__init__()
        self.__disown__()

    def load_buffer(self, bf, obj, buf, sdb):
        print("name: ", bf.file)
        print("size: ", bf.size)
        return True
```

Since Rizin plugins use C function pointers which do not carry state in a consistent manner, ***it is currently only possible to have one director at a time per plugin type*** (eg. `RzBinPlugin`). Setting the current SWIG `RzBinPlugin` director is done using the `RzBinPluginBuilder` class and its `build` method:

```py
# Construct the director
builder = rizin.RzBinPluginBuilder()
builder.name = "SWIGCustom"
builder.enable_load_buffer = True
plugin = builder.build(CustomBinPlugin())
```

`RzBinPluginBuilder::build` returns an `RzBinPlugin` struct which has the enabled function pointers set to custom C functions which call into the currently active director. Enabling functions is done using variables on the builder which are named the same as their corresponding struct function pointer prefixed with `enable_`. To use the plugin, simply append the struct to `core.bin.plugins`.

```py
core = rizin.RzCore()
plugin.thisown = False
core.bin.plugins.append(plugin)
```

Now it is possible to see the `SWIGCustom` plugin when listing the binary plugins with `iL`:

```
... 50 lines before ...
bin  z64         Nintendo 64 binaries big endian rz_bin plugin (LGPL3)
bin  zimg        zimg format bin plugin (LGPL3)
bin  SWIGCustom  (null) (???)
```

To force load a bin with this plugin, use `rz_bin_force_plugin`

```py
core.bin.force_plugin(plugin.name)
core.file_open_load(sys.argv[1])
```

## With helper
Since these steps are generally the same, the bindings define a helper function for Python specifically which uses reflection to determine the overridden methods. The full previous example using the helper is:

```py
import rizin
import sys

class CustomBinPlugin(rizin.RzBinPluginDirector):
    name = "CustomBinPlugin"

    def load_buffer(self, bf, obj, buf, sdb):
        print("name: ", bf.file)
        print("size: ", bf.size)
        return True

plugin, plugin_struct = rizin.register_RzBinPlugin(CustomBinPlugin)

core = rizin.RzCore()
plugin_struct.thisown = False
core.bin.plugins.append(plugin_struct)

# Run rizin and load binary
core.bin.force_plugin(plugin.name)
core.file_open_load(sys.argv[1])
```

## Example
Here's an example which uses the angr cle binary loader to populate the symbols and sections in Rizin.

```py
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
            binmap.perm = segment.flags # must be readable
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
```
