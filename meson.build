project('rz-bindgen', 'c')

rizin = subproject('rizin', default_options: 'cli=enabled')

pymod = import('python')
py_installation = pymod.find_installation('python')

py_installation.extension_module(
  '_rizin',
  'rizin_wrap.c',
  dependencies: [py_installation.dependency(), dependency('rz_main_dep', fallback: ['rizin', 'rz_main_dep'])]
)