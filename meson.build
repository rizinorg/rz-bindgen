project('rz-bindgen', 'c')

pymod = import('python')
py_installation = pymod.find_installation('python')

swig_sources = custom_target(
  'swig_sources',
  input: 'main.py',
  output: 'rizin.i',
  command: [
    py_installation,
    '@INPUT@',
    '-o', '@OUTPUT@',
    '--clang-path', get_option('clang_path'),
    '--clang-args', get_option('clang_args'),
    '--rizin-inc-path', get_option('rizin_inc_path')
  ]
)

swig_wrap = custom_target(
  'swig_wrap',
  input: swig_sources,
  output: 'rizin_wrap.c',
  command: [
    find_program('swig'),
    '-python',
    '-o', '@OUTPUT@', '@INPUT@'
  ]
)

rizin_inc_path = get_option('rizin_inc_path')

py_installation.extension_module(
  '_rizin',
  swig_wrap,
  dependencies: [
    py_installation.dependency(),
    dependency('openssl'),
    dependency('rz_main')
  ],
  include_directories: include_directories(
    rizin_inc_path,
    rizin_inc_path / 'sdb'
  )
)