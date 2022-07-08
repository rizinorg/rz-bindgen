project('rz-bindgen', 'c', 'cpp')

pymod = import('python')
py = pymod.find_installation('python')

clang_path = get_option('clang_path')
clang_args = get_option('clang_args')
rizin_inc_path = get_option('rizin_inc_path')

if clang_path == ''
  clang_path = dependency('llvm', required: false).get_variable(configtool: 'libdir', default_value: 'none')
endif

if rizin_inc_path == ''
  rizin_inc_path = dependency('rz_main').get_pkgconfig_variable('includedir') / 'librz'
endif

if clang_args == ''
  clang_args += ' -resource-dir=' + run_command(meson.get_compiler('c'), '-print-resource-dir').stdout().strip()
endif

swig_sources = custom_target(
  'swig_sources',
  input: 'main.py',
  output: 'rizin.i',
  command: [
    py, '@INPUT@',
    '-o', '@OUTPUT@',
    '--clang-path', clang_path,
    '--clang-args', clang_args,
    '--rizin-inc-path', rizin_inc_path
  ]
)

swig_output = custom_target(
  'swig_output',
  input: swig_sources,
  output: ['rizin_wrap.c', 'rizin.py'],
  command: [
    find_program('swig'),
    '-python',
    '-outdir', '@OUTDIR@', '@INPUT@'
  ]
)
swig_wrap = swig_output[0]
swig_py = swig_output[1]

py.extension_module(
  '_rizin',
  swig_wrap,
  dependencies: [
    py.dependency(),
    dependency('openssl', required: false),
    dependency('rz_main')
  ],
  include_directories: include_directories(
    rizin_inc_path,
    rizin_inc_path / 'sdb'
  ),
  install: true
)
