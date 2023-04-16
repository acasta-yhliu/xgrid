import struct
from typing import Any
from xgrid.lang import boundary, c
from xgrid.lang.operator import kernel, function, external
from xgrid.util.init import init
from xgrid.util.typing import BaseType, Void
from xgrid.util.typing.annotation import ptr, grid
from xgrid.util.typing.value import Integer
from xgrid.util.typing.reference import Grid as _Grid
from xgrid.xgrid import Grid


def _dimension_typecheck(args: list[BaseType]) -> BaseType:
    if not isinstance(args[0], _Grid):
        raise Exception(f"Incompatible dimension to type '{args[0]}'")

    return Integer(struct.calcsize("i"))


def _shape_typecheck(args: list[BaseType]) -> BaseType:
    if not isinstance(args[0], _Grid):
        raise Exception(f"Incompatible shape to type '{args[0]}'")

    if not isinstance(args[1], Integer):
        raise Exception(f"Incompatible shape dimension '{args[1]}'")

    return Integer(struct.calcsize("i"))


def _tick_typecheck(args: list[BaseType]) -> BaseType:
    if not isinstance(args[0], _Grid):
        raise Exception(f"Incompatible tick to type '{args[0]}'")

    return Void()


@external(typecheck_override=_dimension_typecheck)
def dimension(grid: Any) -> int:
    ...


@external(typecheck_override=_shape_typecheck)
def shape(grid: Any, dimension: int) -> int:
    ...


@external(typecheck_override=_tick_typecheck)
def tick(grid: Any) -> None:
    ...


__all__ = ["kernel", "function", "init",
           "ptr", "grid", "boundary", "c", "external", "Grid", "shape", "dimension", "tick"]
