project('rz-bindgen', 'c', 'cpp',
  version: '0.5.1',
  license: 'LGPL3',
  meson_version: '>=0.53.0',
  default_options: ['python.install_env=auto'])

pymod = import('python')
fs = import('fs')
py = pymod.find_installation()

clang_path = get_option('clang_path')
clang_args = get_option('clang_args')
rizin_include_path = get_option('rizin_include_path')
targets = get_option('targets')

target_swig = targets.contains('SWIG')
target_sphinx = targets.contains('sphinx')

doxygen_path = get_option('doxygen_path')

if clang_path == ''
  llvm = dependency('llvm', required: false)
  if llvm.found()
    clang_path = llvm.get_variable(configtool: 'libdir', default_value: 'none')
  elif build_machine.system() == 'darwin'
    clang_path = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/'
  elif build_machine.system() == 'windows'
    clang_path = import('fs').parent(find_program('clang.exe').full_path())
  else
    clang_path = '/usr/lib/'
  endif
endif

if not fs.exists(clang_path)
  error('CLang path does not exist')
endif

rz_core = disabler()
if rizin_include_path == ''
  rz_core = dependency('rz_core')
  if rz_core.type_name() == 'pkgconfig'
    rizin_include_path = rz_core.get_variable(pkgconfig: 'includedir') / 'librz'
  elif rz_core.type_name() == 'cmake'
    rizin_include_path = rz_core.get_variable(cmake: 'PACKAGE_INCLUDE_DIRS').split(';')[0]
  endif
endif

if clang_args == ''
  clang = find_program('clang', 'clang-7', required: false)
  if clang.found()
    clang_args += ' -resource-dir='
    clang_args += run_command(clang, '-print-resource-dir', check: true).stdout().strip()
  endif
  if build_machine.system() == 'darwin'
    clang_args += ' -isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
  endif
endif

bindgen_output_names = []
if target_swig
  swig_source_idx = bindgen_output_names.length()
  bindgen_output_names += ['rizin.i']
endif

if target_sphinx
  sphinx_dir_idx = bindgen_output_names.length()
  bindgen_output_names += ['sphinx']
endif

summary({
  'Rizin include path': rizin_include_path,
  'Clang path': clang_path,
})

if target_swig or target_sphinx
  src_files = files(
    'src/binding_class.py',
    'src/binding_director.py',
    'src/binding_enum.py',
    'src/binding_func.py',
    'src/binding_generic.py',
    'src/binding_generic_specializations.py',
    'src/binding_typemap.py',
    'src/bindings.py',
    'src/cparser_header.py',
    'src/cparser_types.py',
    'src/generator_sphinx.py',
    'src/generator_swig.py',
    'src/lint.py',
    'src/main.py',
    'src/writer.py',
  )

  bindgen_outputs = custom_target(
    'bindgen_outputs',
    input: 'src' / 'main.py',
    output: bindgen_output_names,
    depend_files: src_files,
    command: [
      py, '@INPUT@',
      '-o', '@OUTDIR@',
      '--clang-path', clang_path,
      '--clang-args', clang_args,
      '--rizin-include-path', rizin_include_path,
      '--targets', ','.join(targets)
    ] + (doxygen_path != '' ? ['--doxygen-path', doxygen_path] : [])
  )
endif

if target_swig
  swig_output = custom_target(
    'swig_output',
    input: bindgen_outputs[swig_source_idx],
    output: ['rizin.py', 'rizin_wrap.cxx'],
    command: [
      find_program('swig'),
      '-python', '-c++',
      '-outdir', '@OUTDIR@', '@INPUT@'
    ],
    install: true,
    install_dir: [py.get_install_dir(), false]
  )
  swig_py = swig_output[0]
  swig_wrap = swig_output[1]

  if not rz_core.found()
    rz_core = dependency('rz_core')
  endif

  py.extension_module(
    '_rizin',
    swig_wrap,
    dependencies: [
      py.dependency(),
      rz_core,
    ],
    install: true,
  )
endif

if target_sphinx
  custom_target(
    'sphinx',
    input: bindgen_outputs[sphinx_dir_idx],
    output: 'sphinx_output',
    command: [
      find_program('sphinx-build'),
      '@INPUT@',
      '@OUTPUT@'
    ],
    build_by_default: true
  )
endif

if get_option('plugin').enabled()
  subdir('plugin')
endif
