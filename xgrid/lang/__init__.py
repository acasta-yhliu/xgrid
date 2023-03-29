import sys
from typing import Any, TextIO
from xgrid.lang.ir.statement import Definition

from xgrid.lang.parser import Parser
from xgrid.util.console import ElementFormat
from xgrid.util.logging import Logger


class Operator:
    def __init__(self, func, mode: str) -> None:
        self.func = func
        self.mode = mode

        self.logger = Logger(self)

    def __call__(self, *args: Any) -> Any:
        self.logger.dead("todo")

    @property
    def name(self) -> str:
        return self.func.__name__

    @property
    def ir(self) -> Definition:
        _ir = getattr(self, "_ir", None)
        if _ir is None:
            self._ir = Parser(self.func, self.mode).result
        return self._ir

    def print_ir(self, *, indent: int = 2, device: TextIO = sys.stdout):
        formatter = ElementFormat(indent)
        self.ir.write(formatter)
        formatter.write(device)


def kernel(func):
    return Operator(func, "kernel")


def function(func):
    return Operator(func, "function")


def extern(func):
    return Operator(func, "extern")


class StubContext:
    def __enter__(self):
        pass

    def __exit__(self, a, b, c):
        pass


def c() -> StubContext:
    ...


def critical() -> StubContext:
    ...
