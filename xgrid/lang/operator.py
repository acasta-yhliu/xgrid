import sys
from typing import Any, TextIO
from xgrid.lang.ir.statement import Definition
from xgrid.lang.parser import Parser
from xgrid.util.console import ElementFormat

from xgrid.util.logging import Logger


class Operator:
    def __init__(self, func, mode: str, name: str | None = None, includes: list[str] | None = None) -> None:
        self.func = func
        self.mode = mode

        self.logger = Logger(self)

        self.name = func.__name__ if name is None else name
        self.includes = [] if includes is None else includes
        
        self.native = None

    def __call__(self, *args: Any) -> Any:
        if self.mode == "kernel":
            if self.native is None:
                from xgrid.lang.generator import Generator
                self.native = Generator(self).native
            
            return self.native(*args)
        else:
            self.logger.dead(
                f"Invalid call to non-kernel ({self.mode}) operator '{self.name}'")

    @property
    def ir(self) -> Definition:
        _ir = getattr(self, "_ir", None)
        if _ir is None:
            self._ir = Parser(self.func, self.name, self.mode).result
        return self._ir

    @property
    def source(self) -> str:
        from xgrid.lang.generator import Generator
        return Generator(self).source

    def print_ir(self, *, indent: int = 2, device: TextIO = sys.stdout):
        formatter = ElementFormat(indent)
        self.ir.write(formatter)
        formatter.write(device)


def kernel(*, name: str | None = None, includes: list[str] | None = None):
    def aux(func):
        return Operator(func, "kernel", name, includes)
    return aux


def function(*, name: str | None = None, includes: list[str] | None = None):
    def aux(func):
        return Operator(func, "function", name, includes)
    return aux


def external(*, name: str | None = None, includes: list[str] | None = None):
    def aux(func):
        return Operator(func, "external", name, includes)
    return aux
