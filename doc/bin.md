# rz_bin.h

## The RzBin struct
An `RzBin` struct contains information about the binaries in a Rizin program.
Most importantly, it contains `binfiles` - an `RzList` containing `RzBinFile`.
The main instance is accessible in the `bin` field of an `RzCore` struct.

## The RzBinFile struct
An `RzBinFile` struct does not contain much itself except for the `RzBuffer` corresponding to that file. Most of the important information is in the `o` field, which points to an `RzBinObject` struct.

## The RzBinObject struct
An `RzBinObject` contains most of the information about a binary, including its symbols, entries, and sections.

It's possible to augment Rizin's existing binary format handling by modifying these bin objects from the SWIG bindings. It's also possible to create plugins in supported binding languages to add support for new formats.
