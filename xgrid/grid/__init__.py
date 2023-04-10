from xgrid.util.logging import Logger
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.value import Value


class Grid:
    def __init__(self, shape: tuple[int, ...], dtype: type) -> None:
        self.logger = Logger(self)

        dtype_parsed = parse_annotation(dtype)
        if not isinstance(dtype_parsed, Value):
            self.logger.dead(
                f"Grid element should be value instead of '{dtype_parsed}'")

        self.shape = shape
        
        

    @property
    def dimension(self):
        return len(self.shape)
