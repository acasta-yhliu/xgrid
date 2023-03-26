from typing import Any

from xgrid.lang.parser import Parser


class Operator:
    def __init__(self, func, mode: str) -> None:
        self.func = func
        self.mode = mode

    def __call__(self, *args: Any) -> Any:
        self.ir = Parser(self.func, self.mode).result
        return self.ir


def kernel(func):
    return Operator(func, "kernel")


def function(func):
    return Operator(func, "function")
