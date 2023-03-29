from dataclasses import fields, is_dataclass
from typing import Generic, TypeVar, get_args, get_origin

from xgrid.util.typing import BaseType, Void
import xgrid.util.typing.value as val
import xgrid.util.typing.reference as ref


Length = TypeVar("Length")


class Annotation:
    __concrete_annotation__ = False


class ValueAnnotation(Annotation):
    pass


class Bool(ValueAnnotation):
    pass


class Int(ValueAnnotation, Generic[Length]):
    pass


class Float(ValueAnnotation, Generic[Length]):
    pass


Value = TypeVar("Value", bound=ValueAnnotation)


class ReferenceAnnotation(Annotation):
    pass


class Ptr(ReferenceAnnotation, Generic[Value]):
    pass


class Grid(ReferenceAnnotation, Generic[Value, Length]):
    pass


def parse_annotation(annotation) -> BaseType | None:
    if annotation is None:
        return Void()

    if isinstance(annotation, ValueAnnotation):
        if annotation == Bool:
            return val.Boolean()

        org, arg = get_origin(annotation), get_args(annotation)
        if len(arg) != 1 or type(arg[0]) != int or org is None:
            return None

        range, ctor = {
            Int: ((8, 16, 32, 64), val.Integer),
            Float: ((32, 64), val.Floating)
        }[org]

        if arg[0] not in range:
            return None
        return ctor(arg[0] // 8)

    if isinstance(annotation, ReferenceAnnotation):
        org, arg = get_origin(annotation), get_args(annotation)

        if len(arg) not in (1, 2) or org is None:
            return None

        val_type = parse_annotation(arg[0])
        if not isinstance(val_type, val.Value):
            return None

        if org == Ptr and len(arg) == 1:
            return ref.Pointer(val_type)

        if org == Grid and len(arg) == 2 and type(arg[1]) == int:
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
