# MakeMake
MakeMake is a simple script for the soul purpose of creating a Makefile for my projects

# Format
MakeMake configuration file is written in JSON

The following sections are supported at this time and are the only sections that will be parsed 

1. `globals`: Its purpose it to define variables that you might use in the config file, you can access them by following this syntax: `$(<global-name>)`. Note global variables can also be defined in other sections and they will follow this syntax: `$(<section-name>.<name>)`.
2. `settings`: Its purpose is to define certain settings that MakeMake uses
    1. `src-c-dir` The directory to your C source files
    2. `src-cpp-dir` The directory to your C++ soruce files
    3. `out-type` The type of the output (currently only `executable` is supported)
3. `executable` A section that is required only when the `out-type` is `executable`
    1. `name` the name of the executable
4. `cxx` Its purpose is to define compiler related arguments
    1. `standard` The C++ standard
    2. `compiler` The compiler
    3. `build-dir` The directory where the object files will be stored
    4. `flags` A array with the flags that the compiler will use
5. `include-dirs` A list of the include directories for your project
6. `library-dirs` A list of the directories for the libraries
7. `libraries` The libraries that the executable will be linked against
8. `source-files` A list for your source files
9. `directories-to-create` A list of directories that make will need to create for this program to function properly. It is suggested to add at least the `build-dir` directory.