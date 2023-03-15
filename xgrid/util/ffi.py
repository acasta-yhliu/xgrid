import os
from hashlib import md5
from shutil import which
from subprocess import PIPE, Popen
from typing import IO, Iterable, cast

from xgrid.util.logging import Logger


class Jit:
    "jit driver to perform compiling and linking to dynamic library"

    def __init__(self, name: str, *, cc: list[str] = ["gcc", "clang"]) -> None:
        self.logger = Logger(
            f"{self.__module__}.{self.__class__.__qualname__}")

        self.cacheroot = f"./.{name}"
        if not os.path.exists(self.cacheroot):
            os.makedirs(self.cacheroot)

        def search_cc(seq: list[str]) -> str | None:
            for cc in seq:
                which_cc = which(cc)
                if which_cc:
                    return which_cc
            return None

        local_cc = search_cc(cc)
        if local_cc is None:
            self.logger.dead(
                f"jit failed to locate cc in {cc}")
        self.cc: str = local_cc

        self.logger.info(
            f"jit initialized with cacheroot = '{self.cacheroot}', cc = '{self.cc}'")

    def compile(self, source: str, cflags: Iterable[str] = []):
        args = [self.cc, "-fpic", "-shared"]
        args.extend(cflags)

        source = f"// {' '.join(args)}\n" + source

        name = os.path.join(self.cacheroot, md5(
            source.encode()).hexdigest() + ".c")

        cached = False

        if os.path.exists(name):
            with open(name, "r") as sf:
                cached = sf.read() == source

        if not cached:
            with open(name, "w") as sf:
                sf.write(source)

            args.extend([name, "-o", name + ".so"])

            process = Popen(args, stderr=PIPE)
            if process.wait() != 0:
                err_msg = cast(IO[bytes], process.stderr).read().decode()
                self.logger.dead_multiln(
                    [f"failed to compile '{name}' due to:", err_msg])

        self.logger.info(
            f"jit compiled '{name}' {'with' if cached else 'without'} cache")
