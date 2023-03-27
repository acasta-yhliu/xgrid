from dataclasses import dataclass, is_dataclass, fields
from typing import get_origin, get_args
import ctypes

import xgrid.util.typing.annotation as annot
import xgrid.util.typing.value as val
import xgrid.util.typing.reference as ref


@dataclass
class BaseType:
    __concrete_typing__ = False

    @property
    def ctype(self):
        ...

    def serialize(self, value):
        pass

    def deserialize(self, value):
        return value


@dataclass
class Void(BaseType):
    def __repr__(self) -> str:
        return "Void"


def parse_annotation(annotation) -> BaseType | None:
    if annotation is None:
        return Void()

    if isinstance(annotation, annot.ValueAnnotation):
        if annotation == annot.Bool:
            return val.Boolean()

        if annotation == annot.Void:
            return Void()

        org, arg = get_origin(annotation), get_args(annotation)
        if len(arg) != 1 or type(arg[0]) != int or org is None:
            return None

        range, ctor = {
            annot.Int: ((8, 16, 32, 64), val.Integer),
            annot.Float: ((32, 64), val.Floating)
        }[org]

        if arg[0] not in range:
            return None
        return ctor(arg[0] // 8)

    if isinstance(annotation, annot.ReferenceAnnotation):
        org, arg = get_origin(annotation), get_args(annotation)

        if len(arg) not in (1, 2) or org is None:
            return None

        val_type = parse_annotation(arg[0])
        if not isinstance(val_type, val.Value):
            return None

        if org == annot.Ptr and len(arg) == 1:
            return ref.Pointer(val_type)

        if org == annot.Grid and len(arg) == 2 and type(arg[1]) == int:
            return ref.Grid(val_type, arg[1])

    if is_dataclass(annotation) and isinstance(annotation, type):
        elements = []
        for field in fields(annotation):
            t = parse_annotation(field.type)
            if not isinstance(t, val.Value):
                return None
            elements.append((field.name, t))
        return val.Structure(annotation, annotation.__name__, tuple(elements))

    return None
