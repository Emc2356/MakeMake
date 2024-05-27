# MakeMake
MakeMake is a simple script for the soul purpose of creating a Makefile for my projects

# Format
MakeMake configuration file is written in JSON

The following sections are supported at this time and are the only sections that will be parsed 

1. `globals`: Its purpose it to define variables that you might use in the config file, you can access them by following this syntax: `$(<global-name>)`. Note global variables can also be defined in other sections and they will follow this syntax: `$(<section-name>.<name>)`.
1. `settings`: Its purpose is to define certain settings that MakeMake uses
    1. `src-c-dir` The directory to your C source files
    1. `src-cpp-dir` The directory to your C++ soruce files
    1. `out-type` The type of the output (currently only `executable` is supported)
    1. `libraries-dir` this section is required only when the `dependencies` section is specified
1. `executable` A section that is required only when the `out-type` is `executable`
    1. `name` the name of the executable
1. `archive` A section that is required only when the `out-type` is `archive`
    1. `name` the name of the archive
1. `cxx` Its purpose is to define compiler related arguments
    1. `standard` The C++ standard
    1. `compiler` The compiler
    1. `build-dir` The directory where the object files will be stored
    1. `flags` A array with the flags that the compiler will use
1. `include-dirs` A list of the include directories for your project
1. `library-dirs` A list of the directories for the libraries
1. `libraries` The libraries that the executable will be linked against
1. `source-files` A list for your source files
1. `directories-to-create` A list of directories that make will need to create for this program to function properly. It is suggested to add at least the `build-dir` directory.
1. `dependencies` this section specifies a list of dependencies that will be built with the `archive` `out-type`. To use this functionality it is required to set the `settings.out-type` to archive in the local config file and specify `settings.libraries-dir` in your main config file.
    1. `dependencies` section is an object that holds the path to the configuration file with an optional parameter `globals` that specifies global variables that you want the local config file to use **warning** these globals needs to have unique names otherwise the `globals` section in your local configuration file will override them
