from dataclasses import asdict, dataclass
import sys
from typing import Literal
from xgrid.util.logging import Logger


logger = Logger("xgrid")


@dataclass
class Configuration:
    parallel: bool
    cc: list[str]
    cacheroot: str
    comment: bool
    overstep: Literal["none", "limit", "wrap"]
    opt_level: Literal[0, 1, 2, 3]
    precision: Literal["float", "double"]

    def __repr__(self) -> str:
        return repr(asdict(self))

    @property
    def cflags(self):
        flags = []

        if self.parallel:
            flags.append("-fopenmp")

        flags.append(f"-O{self.opt_level}")

        flags.append(f"-lm")

        return flags

    @property
    def fsize(self):
        return 4 if self.precision == "float" else 8


_config: Configuration | None = None


def get_config() -> Configuration:
    if _config is None:
        logger.dead(f"Please call init first to initialize")
    return _config


def init(*, parallel: bool = True, cc: list[str] = ["gcc", "clang"], cacheroot: str = ".xgrid", comment: bool = False, overstep: Literal["none", "limit", "wrap"] = "none", opt_level: Literal[0, 1, 2, 3] = 2, precision: Literal["float", "double"] = "float") -> None:
    global _config

    if sys.version_info < (3, 10):
        logger.fail(
            f"Minimum Python 3.10 is required, current version is {sys.version_info}")

    if sys.platform == "win32":
        if not any(filter(shutil.which, cc)):
            solutions = ["    1. LLVM (https://llvm.org/)",
                         "    2. MinGW-w64 (https://www.mingw-w64.org/)",
                         "    3. MSYS2 (https://www.msys2.org/)",
                         "    4. Cygwin (https://www.cygwin.com/)"]
            logger.fail(
                f"Failed to find cc within {cc}, possible solutions are:", *solutions)

    _config = Configuration(parallel, cc, cacheroot,
                            comment, overstep, opt_level, precision)

    logger.info(f"initialized with configuration: {_config}")
