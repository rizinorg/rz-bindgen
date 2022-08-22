swig_runtime = custom_target(
  'swig_runtime',
  output: 'swig_runtime.h',
  command: [
    find_program('swig'),
    '-python',
    '-external-runtime', '@OUTPUT@'
  ]
)

library(
  'rz-bindings-plugin',
  ['plugin.c', swig_runtime],
  dependencies: [
    py.dependency(embed: true),
    dependency('openssl', required: false),
    dependency('rz_main')
  ],
)
