swig_runtime = custom_target(
  'swig_runtime',
  output: 'swig_runtime.h',
  command: [
    find_program('swig'),
    '-python',
    '-external-runtime', '@OUTPUT@'
  ]
)

rz_core_dep = dependency('rz_core')
rizin_plugdir = rz_core_dep.get_variable(pkgconfig: 'plugindir', cmake: 'rz_core_PLUGINDIR')

library(
  'rz-bindings-plugin',
  ['plugin.c', swig_runtime],
  dependencies: [
    py.dependency(embed: true),
    dependency('openssl', required: false),
    rz_core_dep,
  ],
  install: true,
  install_dir: rizin_plugdir,
)
