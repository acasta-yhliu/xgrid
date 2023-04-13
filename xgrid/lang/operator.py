from typing import Any, Callable
from xgrid.lang.ir.statement import Definition
from xgrid.lang.parser import Parser

from xgrid.util.logging import Logger
from xgrid.util.typing import BaseType
from xgrid.xgrid import Grid as XGrid


CustomTypecheck = Callable[[list[BaseType]], BaseType]


class Operator:
    def __init__(self, func, mode: str, name: str | None = None, includes: list[str] | None = None, self_type: BaseType | None = None, typecheck_override: CustomTypecheck | None = None) -> None:
        self.func = func
        self.mode = mode

        self.logger = Logger(self)

        self.name = func.__name__ if name is None else name
        self.includes = [] if includes is None else includes

        self.native = None
        self.self_type = self_type
        self.typecheck_override = typecheck_override

    def __call__(self, *args: Any) -> Any:
        if self.mode == "kernel":
            if self.native is None:
                from xgrid.lang.generator import Generator

                self.native, self.depth = Generator(self).result

            # tick the field and resize the time step if necessary
            for arg in args:
                if isinstance(arg, XGrid):
                    arg._op_invoke(self.depth)

            return self.native(*args)
        elif self.mode == "function":
            print(*args)
            return self.func(*args)
        else:
            self.logger.dead(
                f"Invalid call to non-kernel or non-function ({self.mode}) operator '{self.name}'")

    @property
    def ir(self) -> Definition:
        _ir = getattr(self, "_ir", None)
        if _ir is None:
            parser = Parser(self.func, self.name, self.mode, self.self_type)
            self._ir = parser.result
            self.includes.extend(parser.includes)
        return self._ir

    @property
    def signature(self):
        return self.ir.signature


def kernel(*, name: str | None = None, includes: list[str] | None = None):
    def aux(func):
        return Operator(func, "kernel", name, includes)
    return aux


def function(*, method: bool = False, name: str | None = None, includes: list[str] | None = None):
    if method:
        def aux_method(func):
            setattr(func, "__xgrid_method", (name, includes))
            return func
        return aux_method
    else:
        def aux(func):
            return Operator(func, "function", name, includes)
        return aux


def external(*, name: str | None = None, includes: list[str] | None = None, typecheck_override: CustomTypecheck):
    def aux(func):
        return Operator(func, "external", name, includes, typecheck_override=typecheck_override)
    return aux
