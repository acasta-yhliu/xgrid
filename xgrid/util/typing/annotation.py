from typing import Generic, TypeVar


Length = TypeVar("Length")


class Annotation:
    __concrete_annotation__ = False


class ValueAnnotation(Annotation):
    pass


class Void(ValueAnnotation):
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
