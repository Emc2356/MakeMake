from pathlib import Path
import json

from pprint import pprint

import shutil
import sys
import os


class Logger:
    silent: bool = False

    def __init__(self, file: os.PathLike | None=None) -> None:
        self.file: os.PathLike | None = file

    def info(self, message: str) -> None:
        if Logger.silent:
            return
        if self.file is not None:
            print(f"[INFO] from file `{self.file}`: {message}", file=sys.stdout)
        else:
            print(f"[INFO] {message}", file=sys.stdout)

    def warn(self, message: str) -> None:
        if Logger.silent:
            return
        if self.file is not None:
            print(f"[WARNING] from file `{self.file}`: {message}", file=sys.stderr)
        else:
            print(f"[WARNING] {message}", file=sys.stderr)

    def error(self, message: str, code: int=1) -> None:
        if self.file is not None:
            print(f"\033[31m[ERROR] from file `{self.file}`: {message}\033[0m", file=sys.stderr)
        else:
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
        self.archive_name: str = ""
        self.source_files: list[str] = []
        self.libraries: list[str] = []
        self.include_directories: list[str] = []
        self.library_directories: list[str] = []
        self.directories_to_create: list[str] = []

        self.dependencies_config_files: dict[str, ConfigFile] = {}

        self.logger: Logger = Logger(self.path)

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
                if isinstance(value, str):
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
            self.logger.error("`globals` section must be a object that contains *only* strings")
        for key, value in self.data["globals"].items():
            if not isinstance(value, str):
                self.logger.error(f"`{value}` value in `globals` section must be a string")
            if not isinstance(key, str):
                self.logger.error(f"`{key}` key in `globals` section must be a string")

            self.add_global(key, value)

    def parse_executable(self) -> None:
        if self.data.get("executable", None) is None:
            self.logger.error("No `executable` section in config file")

        if not isinstance(self.data["executable"], dict):
            self.logger.error("`executable` section must be a object that contains *only* strings")

        if self.data["executable"].get("name", None) is None:
            self.logger.error("no `name` found in executable section")

        if not isinstance(self.data["executable"]["name"], str):
            self.logger.error("`name` field in `executable` section must be a string")

        self.executable_name = self.apply_globals(self.data["executable"]["name"])

        self.add_global("executable.name", self.executable_name)

    def parse_archive(self) -> None:
        if self.data.get("archive", None) is None:
            self.logger.error("No `archive` section in config file")

        if not isinstance(self.data["archive"], dict):
            self.logger.error("`archive` section must be a object that contains *only* strings")

        if self.data["archive"].get("name", None) is None:
            self.logger.error("no `name` found in archive section")

        if not isinstance(self.data["archive"]["name"], str):
            self.logger.error("`name` field in `archive` section must be a string")

        self.archive_name = self.apply_globals(self.data["archive"]["name"])

        self.add_global("archive.name", self.archive_name)

    def parse_cxx(self) -> None:
        if self.data.get("cxx", None) is None:
            self.logger.error("No `cxx` section in config file")

        if not isinstance(self.data["cxx"], dict):
            self.logger.error("`cxx` section must be a object")

        sections = ["standard", "compiler", "release-flags", "debug-flags", "build-dir", "flags"]

        for section in sections:
            if self.data["cxx"].get(section, None) is None:
                self.logger.error(f"no `{section}` found in cxx section")

        for key, value in self.data["cxx"].items():
            self.cxx[key] = value

        if self.cxx.get("standard", None) is None:
            self.logger.error("no `standard` found in cxx section")
        if self.cxx.get("compiler", None) is None:
            self.logger.error("no `compiler` found in cxx section")
        if self.cxx.get("build-dir", None) is None:
            self.logger.error("no `build-dir` found in cxx section")
        if self.cxx.get("flags", None) is None:
            self.logger.error("no `flags` found in cxx section")

        if not isinstance(self.cxx["standard"], str):
            self.logger.error("`standard` field in `cxx` section must be a string")
        if not isinstance(self.cxx["compiler"], str):
            self.logger.error("`compiler` field in `cxx` section must be a string")
        if not isinstance(self.cxx["build-dir"], str):
            self.logger.error("`build-dir` field in `cxx` section must be a string")
        if not isinstance(self.cxx["flags"], list):
            self.logger.error("`flags` field in `cxx` section must be a array")
        for flag in self.cxx["flags"]:
            if not isinstance(flag, str):
                self.logger.error("`flags` field in `cxx` section must be a array of strings")

        self.cxx["flags"] = " ".join(self.cxx["flags"])


        self.apply_globals(self.cxx, "cxx")

    def parse_include_directories(self) -> None:
        if self.data.get("include-dirs", None) is None:
            self.logger.info("no `include-dirs` section was specified, skipping...")
            return
        self.include_directories = self.data["include-dirs"]
        if not isinstance(self.include_directories, list):
            self.logger.error("`include-dirs` must be a array that contains strings")

        self.apply_globals(self.include_directories)

    def parse_library_directories(self) -> None:
        if self.data.get("library-dirs", None) is None:
            self.logger.info("no `library-dirs` section was specified, skipping...")
            return
        self.library_directories = self.data["library-dirs"]
        if not isinstance(self.library_directories, list):
            self.logger.error("`library-dirs` must be a array that contains strings")

        self.apply_globals(self.library_directories)

    def parse_libraries(self) -> None:
        if self.data.get("libraries", None) is None:
            self.logger.info("no `libraries` section was specified, skipping...")
            return
        self.libraries = self.data["libraries"]
        if not isinstance(self.libraries, list):
            self.logger.error("`libraries` must be a array that contains strings")

        self.apply_globals(self.libraries)

    def parse_source_files(self) -> None:
        if self.data.get("source-files", None) is None:
            self.logger.error("no `source-files` section was specified, skipping...")
        self.source_files = self.data["source-files"]
        if not isinstance(self.source_files, list):
            self.logger.error("`source-files` must be a array that contains strings")

        self.apply_globals(self.source_files)

    def parse_directories_to_create(self) -> None:
        if self.data.get("directories-to-create", None) is None:
            self.logger.info("no `directories-to-create` section was specified, skipping...")
            return
        self.directories_to_create = self.data["directories-to-create"]
        if not isinstance(self.directories_to_create, list):
            self.logger.error("`directories-to-create` must be a array that contains strings")

        self.apply_globals(self.directories_to_create)

    def parse_settings(self) -> None:
        if self.data.get("settings", None) is None:
            self.logger.info("no `settings` section was specified")
            return
        if not isinstance(self.data["settings"], dict):
            self.logger.error("`settings` must be a object that contains *only* strings")

        sections = ["src-c-dir", "src-cpp-dir", "out-type"]

        for section in sections:
            if self.data["settings"].get(section, None) is None:
                self.logger.error(f"no `{section}` found in settings section")
            if not isinstance(self.data["settings"][section], str):
                self.logger.error(f"`{section}` field in `settings` section must be a string")

        self.settings["src-c-dir"] = self.data["settings"]["src-c-dir"]
        self.settings["src-cpp-dir"] = self.data["settings"]["src-cpp-dir"]
        self.settings["out-type"] = self.data["settings"]["out-type"]

        if self.data["settings"].get("libraries-dir", None) is not None:
            if isinstance(self.data["settings"]["libraries-dir"], str):
                self.settings["libraries-dir"] = self.data["settings"]["libraries-dir"]
            else:
                self.logger.error(f"`libraries-dir` field in `settings` section must be a string")

        self.apply_globals(self.settings, "settings")

    def parse_dependencies(self) -> None:
        if self.data.get("dependencies", None) is None:
            self.logger.info("no `dependencies` section was specified, skipping...")
            return

        if self.settings.get("libraries-dir", None) is None:
            self.logger.error("`libraries-dir` must be specified in section `settings` in order to use dependencies")

        dependencies = self.data["dependencies"]

        for config_path, dependency_data in dependencies.items():
            if not Path(config_path).exists():
                self.logger.error(f"dependency `{config_path}` does not exist")
            if not isinstance(dependency_data, dict):
                self.logger.error(f"dependency `{config_path}` must be a object")
            if dependency_data.get("globals", None) is None:
                self.logger.info(f"no `globals` field was specified for dependency `{config_path}`, skipping...")
            if not isinstance(dependency_data["globals"], dict):
                self.logger.error(f"`globals` field in dependency `{config_path}` must be an object")

            dependency_globals: dict[str, str] = {}

            if dependency_data.get("globals", None) is not None:
                for name, value in dependency_data["globals"].items():
                    dependency_globals[name] = self.apply_globals(value)

            config_file = ConfigFile(config_path)

            for name, value in dependency_globals.items():
                config_file.add_global(name, value)

            config_file.parse()

            self.dependencies_config_files[config_path] = config_file

    def parse(self) -> None:
        self.data = self.read_json(self.path)

        self.parse_globals()
        self.parse_settings()
        if self.settings["out-type"] == "executable":
            self.parse_executable()
        elif self.settings["out-type"] == "archive":
            self.parse_archive()
        self.parse_cxx()
        self.parse_include_directories()
        self.parse_library_directories()
        self.parse_libraries()
        self.parse_source_files()
        self.parse_directories_to_create()
        self.parse_dependencies()

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

        have_dependencies = len(self.dependencies_config_files) > 0
        if have_dependencies:
            for name, cfg_file in self.dependencies_config_files.items():
                path_to_library = Path(self.settings["libraries-dir"]) / f"lib{Path(cfg_file.archive_name).name}.a"

                content += f"EXTRA_LABELS += {path_to_library}\n"

        archives = ""

        if have_dependencies:
            for name, cfg_file in self.dependencies_config_files.items():
                path_to_library = Path(self.settings["libraries-dir"]) / f"lib{Path(cfg_file.archive_name).name}.a"

                archives += f"{path_to_library} "

        content += f"{self.executable_name}: $(EXTRA_LABELS) $(OBJECT_FILES)\n"
        content += f"\t$(BASE_CMD) -o {self.executable_name} $(OBJECT_FILES) {archives} $(LIBRARIES)\n"

        content += f'{self.cxx['build-dir']}%.cpp.o: {self.settings["src-cpp-dir"]}%.cpp\n'
        content += f'\t$(BASE_CMD) -c -o $@ $<\n'
        content += f'{self.cxx['build-dir']}%.c.o: {self.settings["src-c-dir"]}%.c\n'
        content += f'\t$(BASE_CMD) -c -o $@ $<\n'

        for directory in self.directories_to_create:
            content += f"{directory}:\n"
            content += f"\tmkdir -p {directory}\n"

        if have_dependencies:
            for name, cfg_file in self.dependencies_config_files.items():
                path_to_library = Path(self.settings["libraries-dir"]) / f"lib{Path(cfg_file.archive_name).name}.a"

                content += f"{path_to_library}:\n"
                content += f"\tmake -f {Path(cfg_file.path).parent / 'Makefile'}\n"

        content += ".PHONY: clean\n"
        content += "clean:\n"
        content += f"\trm -rf {' '.join(self.directories_to_create)}\n"
        content += f"\trm {self.executable_name}\n"
        if have_dependencies:
            for name, cfg_file in self.dependencies_config_files.items():
                content += f"\tmake -f {Path(cfg_file.path).parent / 'Makefile'} clean\n"

        self.write_file(path, content)

    def make_archive(self, path: os.PathLike) -> None:
        content = "# AUTO GENERATED FILE DO NOT EDIT\n\n"

        if len(self.include_directories) > 0:
            content += f"INCLUDE_DIRS = -I" + " -I".join(self.include_directories)
            content += "\n"

        content += f"BASE_CMD = {self.cxx['compiler']} --std=c++{self.cxx['standard']} {self.cxx['flags']} $(INCLUDE_DIRS)\n"

        content += f"OBJECT_FILES = {self.source_to_object_files()}\n"
        content += "EXTRA_LABELS =\n"

        for directory in self.directories_to_create:
            content += f'ifeq ("$(wildcard {directory})", "")\n'
            content += f'EXTRA_LABELS += {directory}\n'
            content += f'endif\n'

        archive_name = Path(self.archive_name).parent / (f"lib{Path(self.archive_name).name}.a")

        content += f"{archive_name}: $(EXTRA_LABELS) $(OBJECT_FILES)\n"
        content += f"\tar rc -o {archive_name} $(OBJECT_FILES)\n"


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
        content += f"\t"

        self.write_file(path, content)

    def make(self, path: os.PathLike) -> None:
        if self.settings["out-type"] == "executable":
            self.make_executable(path)
            if len(self.dependencies_config_files) > 0:
                for config_path, config_file in self.dependencies_config_files.items():
                    config_file.make(Path(config_file.path).parent / "Makefile")
        elif self.settings["out-type"] == "archive":
            self.make_archive(path)
        else:
            self.logger.error(f"unknown output type `{self.settings['out-type']}` propably a MakeMake problem")

    def clean(self) -> None:
        try:
            self.logger.info(f"attempting to remove Makefile...")
            Path("./Makefile").unlink()
        except FileNotFoundError:
            self.logger.info(f"Makefile not found")

        for path in self.directories_to_create:
            try:
                self.logger.info(f"attempting to remove {path}...")
                shutil.rmtree(path)
            except FileNotFoundError:
                self.logger.info(f"{path} not found")

        if len(self.dependencies_config_files) > 0:
            for config_path, config_file in self.dependencies_config_files.items():
                try:
                    self.logger.info(f"attempting to remove {Path(config_file.path).parent / 'Makefile'}...")
                    (Path(config_file.path).parent / "Makefile").unlink()
                except FileNotFoundError:
                    self.logger.info(f"{Path(config_file.path).parent / 'Makefile'} not found")

                for path in config_file.directories_to_create:
                    try:
                        self.logger.info(f"attempting to remove {path}...")
                        shutil.rmtree(path)
                    except FileNotFoundError:
                        self.logger.info(f"{path} not found")

    @staticmethod
    def read_json(path: os.PathLike) -> None:
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def write_file(path: os.PathLike, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    def format(self) -> str:
        data = {
            "path": self.path,
            "globals": self.globals,
            "settings": self.settings,
            "cxx": self.cxx,
            "source_files": self.source_files,
            "libraries": self.libraries,
            "include_directories": self.include_directories,
            "library_directories": self.library_directories,
            "directories_to_create": self.directories_to_create,
        }
        if self.settings["out-type"] == "executable":
            data["executable_name"] = self.executable_name
        elif self.settings["out-type"] == "archive":
            data["archive_name"] = self.archive_name
        else:
            self.logger.error(f"unknown output type `{self.settings['out-type']}` propably a MakeMake error")
        if len(self.dependencies_config_files) > 0:
            data["dependencies_config_files"] = {}
            for name, cfg_file in self.dependencies_config_files.items():
                data["dependencies_config_files"][name] = cfg_file.format()

        return data


def consume_arg(arguments: list[str], target: str) -> bool:
    for argument in arguments:
        if argument == target:
            arguments.remove(argument)
            return True
    return False


def usage(out) -> None:
    print(f"Usage: {sys.argv[0]} [config-file]", file=out)
    print("If no config file is given the default one will be used (cfg.json)", file=out)
    print("If no config file is given and no default config file is found it exits with code 1", file=out)
    print("    --silent silence info and warnings", file=out)
    print("    -f --file specify the config file", file=out)
    print("    -h --help display this message", file=out)
    print("    --clean cleans up ALL the files generated by MakeMake and everything that the Makefiles have generated", file=out)


def main() -> None:
    logger: Logger = Logger()

    argv = sys.argv[:]

    make_clean: bool = False

    if consume_arg(argv, "-h") or consume_arg(argv, "--help"):
        usage(sys.stdout)
        sys.exit(0)

    if consume_arg(argv, "--silent"):
        Logger.silent = True

    if consume_arg(argv, "--clean"):
        make_clean = True

    file: str
    if len(argv) < 2:
        logger.info("No config file specified, using default")
        file = "cfg.json"
        if not os.path.exists(file):
            logger.error("no configuration file given nor the default one was found", 1)
    elif len(argv) == 2:
        file = argv[1]
        if not os.path.exists(file):
            logger.error(f"Config file `{file}` found", 1)
    elif len(argv) == 3:
        argv1 = argv[1]
        if argv1 == "-f" or argv1 == "--file":
            file = argv[2]
            if not os.path.exists(file):
                logger.error(f"Config file `{file}` found", 1)
        else:
            logger.error("Too many arguments", 0)
            usage(sys.stderr)
            sys.exit(1)
    else:
        logger.error("Too many arguments", 0)
        usage(sys.stderr)
        sys.exit(1)

    logger.info(f"Using config file `{file}`")

    config_file: ConfigFile = ConfigFile(file)

    config_file.parse()

    if make_clean:
        logger.info("cleaning up...")
        config_file.clean()
        logger.info("done")
        sys.exit(0)

    config_file.make("./Makefile")


if __name__ == "__main__":
    main()
