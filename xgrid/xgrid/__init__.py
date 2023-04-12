import numpy as np
from xgrid.util.logging import Logger
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.value import Value
import xgrid.util.typing.reference as ref

from ctypes import c_int32, POINTER


def parse_numpy_dtype(dtype: Value):
    # TODO: parse this into numpy dtype
    return np.float32


class Grid:
    def __init__(self, shape: tuple[int, ...], dtype: type) -> None:
        self.logger = Logger(self)

        dtype_parsed = parse_annotation(dtype)
        if not isinstance(dtype_parsed, Value):
            self.logger.dead(
                f"Grid element should be value instead of '{dtype_parsed}'")
        numpy_dtype = parse_numpy_dtype(dtype_parsed)

        # properties
        self.element = dtype_parsed
        self.shape = shape

        # internal typing used for serialization
        self.typing = ref.Grid(self.element, self.dimension)

        # data layout
        self._time_idx = 0
        self._time_ttl = 1
        self._data = [np.zeros(shape=shape, dtype=numpy_dtype)]

        # boundary condition
        self._boundary_mask = np.zeros(shape=shape, dtype=np.int32)
        self._boundary_value = np.zeros(shape=shape, dtype=numpy_dtype)

    @property
    def dimension(self):
        return len(self.shape)

    def serialize(self):
        boundary_mask = self._boundary_mask.ctypes.data_as(POINTER(c_int32))
        boundary_value = self._boundary_value.ctypes.data_as(
            POINTER(self.element.ctype))
        data = (POINTER(self.element.ctype) * self._time_ttl)(*
                                                              list(map(lambda x: x.ctypes.data_as(POINTER(self.element.ctype)), self._data)))

        return self.typing.ctype(self._time_idx,
                                 self._time_ttl,
                                 (c_int32 * self.dimension)(*self.shape),
                                 data,
                                 boundary_mask,
                                 boundary_value)

    def tick(self):
        self._time_idx = (self._time_idx + 1) % self._time_ttl

    @property
    def now(self):
        return self._data[self._time_idx]

    def __getitem__(self, slice):
        return self._data[self._time_idx][slice]

    def __setitem__(self, slice, value):
        self._data[self._time_idx][slice] = value
