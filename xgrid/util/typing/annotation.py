from dataclasses import fields, is_dataclass
import struct
from typing import Any, Generic, TypeVar, get_args, get_origin

from xgrid.util.typing import BaseType, Void
import xgrid.util.typing.value as val
import xgrid.util.typing.reference as ref


Length = TypeVar("Length")


Value = TypeVar("Value")


class Annotation:
    ...


class ptr(Annotation, Generic[Value]):
    def addr(self) -> int: ...


class grid(Annotation, Generic[Value, Length]):
    def __getitem__(self, key) -> Any: ...

    def __setitem__(self, key, value) -> Any: ...


def parse_annotation(annotation, glbs = globals()) -> BaseType | None:
    if annotation is None:
        return Void()
    
    if type(annotation) == str:
        annotation = glbs[annotation]

    if annotation in (int, float, bool):
        return {int: val.Integer(struct.calcsize("i")), float: val.Floating(struct.calcsize("f")), bool: val.Boolean()}[annotation]

    if is_dataclass(annotation) and isinstance(annotation, type):
        elements = []
        for field in fields(annotation):
            t = parse_annotation(field.type)
            if not isinstance(t, val.Value):
                return None
            elements.append((field.name, t))
        return val.Structure(annotation, annotation.__name__, tuple(elements))

    org, arg = get_origin(annotation), get_args(annotation)

    if len(arg) not in (1, 2) or org is None:
        return None

    val_type = parse_annotation(arg[0])
    if not isinstance(val_type, val.Value):
        return None

    if org == ptr and len(arg) == 1:
        return ref.Pointer(val_type)

    if org == grid and len(arg) == 2 and type(arg[1]) == int:
        return ref.Grid(val_type, arg[1])

    return None
