import ctypes
from xgrid.util.logging import Logger
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.value import Value
import xgrid.util.typing.reference as ref


class Grid:
    def __init__(self, shape: tuple[int, ...], dtype: type) -> None:
        self.logger = Logger(self)

        dtype_parsed = parse_annotation(dtype)
        if not isinstance(dtype_parsed, Value):
            self.logger.dead(
                f"Grid element should be value instead of '{dtype_parsed}'")

        self.element = dtype_parsed
        self.shape = shape

        self.typing = ref.Grid(self.element, self.dimension)

        # TODO: implement grid data layout and serialization

    @property
    def dimension(self):
        return len(self.shape)
