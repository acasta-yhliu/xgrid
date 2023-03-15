import os
import ctypes
from hashlib import md5
from shutil import which
from subprocess import PIPE, Popen
from typing import IO, Callable, Iterable, cast

from xgrid.util.logging import Logger
from xgrid.util.typing import BaseType
from xgrid.util.typing.value import Void


class Library:
    def __init__(self, name: str) -> None:
        self.logger = Logger(self)
        self.dylib = ctypes.cdll.LoadLibrary(name)

    def function(self, entry_point: str, argtypes: list[BaseType], restype: BaseType) -> Callable:
        handler = getattr(self.dylib, entry_point)
        if not handler:
            self.logger.dead(f"failed to get function '{entry_point}")

        for argt in argtypes:
            if isinstance(argt, Void):
                self.logger.dead("unexpected void type in arguments")

        if not isinstance(restype, Void):
            handler.restype = restype.ctype

        def wrapper(*args):
            if len(args) != len(argtypes):
                raise TypeError(
                    f"this function takes {len(argtypes)} argument ({len(args)} given)")
            return restype.deserialize(handler(*map(lambda x: x[0](x[1]), zip(map(lambda x: x.serialize, argtypes), args))))
        return wrapper


class Compiler:
    "compiler driver to perform compiling and linking to dynamic library"

    def __init__(self, *, cacheroot: str, cc: Iterable[str]) -> None:
        self.logger = Logger(self)

        self.cacheroot = os.path.join(".", cacheroot)
        if not os.path.exists(self.cacheroot):
            os.makedirs(self.cacheroot)

        def search_cc(seq: Iterable[str]) -> str:
            for cc in seq:
                which_cc = which(cc)
                if which_cc:
                    return which_cc
            self.logger.dead(f"failed to locate cc in {seq}")
        self.cc = search_cc(cc)

        self.logger.info(
            f"compiler initialized with cacheroot = '{self.cacheroot}', cc = '{self.cc}'")

    def compile(self, source: str, cflags: Iterable[str] = []):
        args = [self.cc, "-fpic", "-shared"]
        args.extend(cflags)

        source = f"// {' '.join(args)}\n" + source

        name = os.path.join(self.cacheroot, md5(
            source.encode()).hexdigest() + ".c")
        libname = name + ".so"

        cached = False

        if os.path.exists(name):
            with open(name, "r") as sf:
                cached = sf.read() == source

        if not cached:
            with open(name, "w") as sf:
                sf.write(source)

            args.extend([name, "-o", libname])

            process = Popen(args, stderr=PIPE)
            if process.wait() != 0:
                err_msg = cast(IO[bytes], process.stderr).read().decode()
                self.logger.dead(
                    f"failed to compile '{name}' due to:", err_msg)

        self.logger.info(
            f"jit compiled '{name}' {'with' if cached else 'without'} cache to '{libname}'")

        return libname
