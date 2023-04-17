import numpy as np
from xgrid.util.logging import Logger
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.value import Boolean, Floating, Integer, Structure, Value
import xgrid.util.typing.reference as ref

from ctypes import c_int32, POINTER


def parse_numpy_dtype(dtype: Value):
    if isinstance(dtype, Boolean):
        return np.bool_
    elif isinstance(dtype, Integer):
        return {8: np.int8, 16: np.int16, 32: np.int32, 64: np.int64}[dtype.width_bits]
    elif isinstance(dtype, Floating):
        return {32: np.float32, 64: np.float64}[dtype.width_bits]
    elif isinstance(dtype, Structure):
        return [(x[0], parse_numpy_dtype(x[1])) for x in dtype.elements]


class Grid:
    def __init__(self, shape: tuple[int, ...], dtype: type) -> None:
        self.logger = Logger(self)

        dtype_parsed = parse_annotation(dtype)
        if not isinstance(dtype_parsed, Value):
            self.logger.dead(
                f"Grid element should be value instead of '{dtype_parsed}'")
        self.numpy_dtype = parse_numpy_dtype(dtype_parsed)

        # properties
        self.element = dtype_parsed
        self.shape = shape

        # internal typing used for serialization
        self.typing = ref.Grid(self.element, self.dimension)

        self._data = [np.zeros(shape=shape, dtype=self.numpy_dtype)]

        # boundary condition
        self.boundary = np.zeros(shape=shape, dtype=np.int32)

    def _extend_time(self, depth: int):
        while len(self._data) < depth:
            self._data.append(
                np.zeros(shape=self.shape, dtype=self.numpy_dtype))
        self._data = self._data[:depth]

    def _op_invoke(self, depth: int, tick: bool):
        self._extend_time(depth)

        if tick:
            last = self._data.pop()
            self._data.insert(0, last)

    @property
    def dimension(self):
        return len(self.shape)

    def serialize(self):
        boundary_mask = self.boundary.ctypes.data_as(POINTER(c_int32))
        data = (POINTER(self.element.ctype) * len(self._data))(*
                                                               [data.ctypes.data_as(POINTER(self.element.ctype)) for data in self._data])

        return self.typing.ctype(len(self._data),
                                 (c_int32 * self.dimension)(*self.shape),
                                 data,
                                 boundary_mask)

    @property
    def now(self):
        return self._data[0]

    def fill(self, data: np.ndarray, time: int = 0):
        if data.shape != self.now.shape or data.dtype != self.now.dtype:
            self.logger.dead(
                f"Unable to fill grid with incompatible shape or data type")

        self._extend_time(abs(time))
        self._data[time] = data.copy()

    def __getitem__(self, slice):
        return self.now[slice]

    def __setitem__(self, slice, value):
        self.now[slice] = value
