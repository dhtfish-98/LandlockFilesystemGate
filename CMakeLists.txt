cmake_minimum_required(VERSION 3.20)
project(LandlockFilesystemGate VERSION 0.1.0 LANGUAGES C)

add_library(landlock_filesystem_gate STATIC src/landlock_filesystem_gate.c)
target_include_directories(landlock_filesystem_gate PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(landlock_filesystem_gate PUBLIC c_std_11)
target_compile_options(landlock_filesystem_gate PRIVATE -Wall -Wextra -Werror)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  add_executable(landlock-live tests/live_probe.c)
  target_link_libraries(landlock-live PRIVATE landlock_filesystem_gate)
  target_compile_options(landlock-live PRIVATE -Wall -Wextra -Werror)
  # The probe re-executes after READ_FILE is restricted to its test paths.
  # A dynamic loader would need to reopen libc outside those paths.
  target_link_options(landlock-live PRIVATE -static)
endif()

install(TARGETS landlock_filesystem_gate ARCHIVE DESTINATION lib)
install(FILES include/landlock_filesystem_gate.h DESTINATION include)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/项目文档")
  install(DIRECTORY 项目文档/ DESTINATION share/landlock-filesystem-gate/项目文档)
endif()
