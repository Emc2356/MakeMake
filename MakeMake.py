from pathlib import Path
import json

import sys
import os


def warn(message: str) -> None:
    print(f"[WARNING] {message}", file=sys.stderr)


def error(message: str, code: int=1) -> None:
    print(f"\033[31m[ERROR] {message}\033[0m", file=sys.stderr)
    if code != 0:
        sys.exit(code)


class ConfigFile:
    def __init__(self, path: os.PathLike) -> None:
        self.path = path
        self.data: dict

        self.globals: dict[str, str] = {}
        self.cxx: dict[str, str] = {}
        self.settings: dict[str, str] = {}
        self.executable_name: str = ""
        self.source_files: list[str] = []
        self.libraries: list[str] = []
        self.include_directories: list[str] = []
        self.library_directories: list[str] = []
        self.directories_to_create: list[str] = []

    def add_global(self, key: str, value: str) -> None:
        self.globals[key] = self.apply_globals(value)

    def apply_globals(self, target: str | dict | list | None, category="") -> str | dict | list:
        """
        Applies the globals gathered till this point

        :param target: that object that the function will act upon. It can be a string, a dict or a list
        :param category: an optional parameter that effects this function only when a dictonary is passed
        :return: the modified object
        """
        if isinstance(target, str):
            for key, value in self.globals.items():
                target = target.replace(f"$({key})", value)
            return target
        elif isinstance(target, dict):
            for key, value in target.items():
                target[key] = self.apply_globals(value)
                if category != "":
                    self.add_global(f"{category}.{key}", value)
            return target
        elif isinstance(target, list):
            for key, value in enumerate(target):
                target[key] = self.apply_globals(value)
            return target
        else:
            raise RuntimeError(f"Unknown type {type(target)}")

    def parse_globals(self) -> None:
        if self.data.get("globals", None) is None:
            return
        if not isinstance(self.data["globals"], dict):
            error("`globals` section must be a object that contains *only* strings")
        for key, value in self.data["globals"].items():
            if not isinstance(value, str):
                error(f"`{value}` value in `globals` section must be a string")
            if not isinstance(key, str):
                error(f"`{key}` key in `globals` section must be a string")

            self.add_global(key, value)

    def parse_executable(self) -> None:
        if self.data.get("executable", None) is None:
            error("No `executable` section in config file")

        if not isinstance(self.data["executable"], dict):
            error("`executable` section must be a object that contains *only* strings")

        if self.data["executable"].get("name", None) is None:
            error("no `name` found in executable section")

        if not isinstance(self.data["executable"]["name"], str):
            error("`name` field in `executable` section must be a string")

        self.executable_name = self.apply_globals(self.data["executable"]["name"])

        self.add_global("executable.name", self.executable_name)

    def parse_cxx(self) -> None:
        if self.data.get("cxx", None) is None:
            error("No `cxx` section in config file")

        if not isinstance(self.data["cxx"], dict):
            error("`cxx` section must be a object")

        sections = ["standard", "compiler", "release-flags", "debug-flags", "build-dir", "flags"]

        for section in sections:
            if self.data["cxx"].get(section, None) is None:
                error(f"no `{section}` found in cxx section")

        for key, value in self.data["cxx"].items():
            self.cxx[key] = value

        if self.cxx.get("standard", None) is None:
            error("no `standard` found in cxx section")
        if self.cxx.get("compiler", None) is None:
            error("no `compiler` found in cxx section")
        if self.cxx.get("build-dir", None) is None:
            error("no `build-dir` found in cxx section")
        if self.cxx.get("flags", None) is None:
            error("no `flags` found in cxx section")

        if not isinstance(self.cxx["standard"], str):
            error("`standard` field in `cxx` section must be a string")
        if not isinstance(self.cxx["compiler"], str):
            error("`compiler` field in `cxx` section must be a string")
        if not isinstance(self.cxx["build-dir"], str):
            error("`build-dir` field in `cxx` section must be a string")
        if not isinstance(self.cxx["flags"], list):
            error("`flags` field in `cxx` section must be a array")
        for flag in self.cxx["flags"]:
            if not isinstance(flag, str):
                error("`flags` field in `cxx` section must be a array of strings")

        self.cxx["flags"] = " ".join(self.cxx["flags"])


        self.apply_globals(self.cxx, "cxx")

    def parse_include_directories(self) -> None:
        if self.data.get("include-dirs", None) is None:
            warn("no `include-dirs` section was specified")
            return
        self.include_directories = self.data["include-dirs"]
        if not isinstance(self.include_directories, list):
            error("`include-dirs` must be a array that contains strings")

        self.apply_globals(self.include_directories)

    def parse_library_directories(self) -> None:
        if self.data.get("library-dirs", None) is None:
            warn("no `library-dirs` section was specified")
            return
        self.library_directories = self.data["library-dirs"]
        if not isinstance(self.library_directories, list):
            error("`library-dirs` must be a array that contains strings")

        self.apply_globals(self.library_directories)

    def parse_libraries(self) -> None:
        if self.data.get("libraries", None) is None:
            warn("no `libraries` section was specified")
            return
        self.libraries = self.data["libraries"]
        if not isinstance(self.libraries, list):
            error("`libraries` must be a array that contains strings")

        self.apply_globals(self.libraries)

    def parse_source_files(self) -> None:
        if self.data.get("source-files", None) is None:
            error("no `source-files` section was specified")
        self.source_files = self.data["source-files"]
        if not isinstance(self.source_files, list):
            error("`source-files` must be a array that contains strings")

        self.apply_globals(self.source_files)

    def parse_directories_to_create(self) -> None:
        if self.data.get("directories-to-create", None) is None:
            warn("no `directories-to-create` section was specified")
            return
        self.directories_to_create = self.data["directories-to-create"]
        if not isinstance(self.directories_to_create, list):
            error("`directories-to-create` must be a array that contains strings")

        self.apply_globals(self.directories_to_create)

    def parse_settings(self) -> None:
        if self.data.get("settings", None) is None:
            warn("no `settings` section was specified")
            return
        if not isinstance(self.data["settings"], dict):
            error("`settings` must be a object that contains *only* strings")

        sections = ["src-c-dir", "src-cpp-dir", "out-type"]

        for section in sections:
            if self.data["settings"].get(section, None) is None:
                error(f"no `{section}` found in settings section")
            if not isinstance(self.data["settings"][section], str):
                error(f"`{section}` field in `settings` section must be a string")

        self.settings["src-c-dir"] = self.data["settings"]["src-c-dir"]
        self.settings["src-cpp-dir"] = self.data["settings"]["src-cpp-dir"]
        self.settings["out-type"] = self.data["settings"]["out-type"]

        self.apply_globals(self.settings, "settings")

    def parse(self) -> None:
        self.data = self.read_json(self.path)

        self.parse_globals()
        self.parse_settings()
        self.parse_executable()
        self.parse_cxx()
        self.parse_include_directories()
        self.parse_library_directories()
        self.parse_libraries()
        self.parse_source_files()
        self.parse_directories_to_create()

    def source_to_object_files(self) -> str:
        ret = ""
        for file in self.source_files:
            ret += f"{Path(self.cxx['build-dir']) / Path(file).name}.o "

        return ret

    def make_executable(self, path: os.PathLike) -> None:
        content = "# AUTO GENERATED FILE DO NOT EDIT\n\n"

        if len(self.include_directories) > 0:
            content += f"INCLUDE_DIRS = -I" + " -I".join(self.include_directories)
            content += "\n"
        if len(self.library_directories) > 0:
            content += f"LIBRARY_DIRS = -L" + " -L".join(self.library_directories)
            content += "\n"
        if len(self.libraries) > 0:
            content += f"LIBRARIES = -l" + " -l".join(self.libraries)
            content += "\n"

        content += f"BASE_CMD = {self.cxx['compiler']} --std=c++{self.cxx['standard']} {self.cxx['flags']} $(INCLUDE_DIRS)\n"

        content += f"OBJECT_FILES = {self.source_to_object_files()}\n"
        content += "EXTRA_LABELS =\n"

        for directory in self.directories_to_create:
            content += f'ifeq ("$(wildcard {directory})", "")\n'
            content += f'EXTRA_LABELS += {directory}\n'
            content += f'endif\n'


        content += f"{self.executable_name}: $(EXTRA_LABELS) $(OBJECT_FILES)\n"
        content += f"\t$(BASE_CMD) -o {self.executable_name} $(OBJECT_FILES) $(LIBRARIES)\n"

        content += f'{self.cxx['build-dir']}%.cpp.o: {self.settings["src-cpp-dir"]}%.cpp\n'
        content += f'\t$(BASE_CMD) -c -o $@ $<\n'
        content += f'{self.cxx['build-dir']}%.c.o: {self.settings["src-c-dir"]}%.c\n'
        content += f'\t$(BASE_CMD) -c -o $@ $<\n'

        for directory in self.directories_to_create:
            content += f"{directory}:\n"
            content += f"\tmkdir -p {directory}\n"

        content += ".PHONY: clean\n"
        content += "clean:\n"
        content += f"\trm -rf {' '.join(self.directories_to_create)}\n"
        content += f"\trm {self.executable_name}\n"

        self.write_file(path, content)

    def make(self, path: os.PathLike) -> None:
        if self.settings["out-type"] == "executable":
            self.make_executable(path)
        else:
            # TODO: Add support for archives
            error("currently only executables are supported :/")

    @staticmethod
    def read_json(path: os.PathLike) -> None:
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def write_file(path: os.PathLike, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)


def main() -> None:
    file: str
    if len(sys.argv) < 2:
        warn("No config file specified, using default")
        file = "cfg.json"
        if not os.path.exists(file):
            error("no configuration file given nor the default one was found", 1)
    else:
        file = sys.argv[1]
        if not os.path.exists(file):
            error(f"Config file `{file}` found", 1)

    config_file: ConfigFile = ConfigFile(file)

    config_file.parse()
    config_file.make("./Makefile")


if __name__ == "__main__":
    main()

