import sys
import shutil
from xgrid.util.logging import Logger
from xgrid.lang import kernel


logger = Logger("xgrid")


def init(*, parallel: bool = True, cc: list[str] = ["gcc", "clang"]) -> None:
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

    logger.info(f"initialized with parallel = {parallel}, cc = {cc}")


__all__ = ["kernel"]
