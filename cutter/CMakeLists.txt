cmake_minimum_required(VERSION 3.12)
project(cutter-rz-bindings)

find_package(Cutter REQUIRED)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)

add_custom_command(
  OUTPUT swig_runtime.h
  COMMAND swig -python -external-runtime ${CMAKE_CURRENT_BINARY_DIR}/swig_runtime.h
  )

find_package(Python COMPONENTS Development REQUIRED)

include_directories(${Python_INCLUDE_DIRS} ${CMAKE_CURRENT_BINARY_DIR})
add_library(
  cutter_rz_bindings MODULE
  CutterRzBindings.cpp
  PythonConsole.cpp
  PythonConsole.ui
  PythonConsoleWriter.cpp
  )

target_link_libraries(cutter_rz_bindings PRIVATE Cutter::Cutter)
