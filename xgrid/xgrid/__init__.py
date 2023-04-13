import numpy as np
from xgrid.util.logging import Logger
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.value import Boolean, Floating, Integer, Structure, Value
import xgrid.util.typing.reference as ref

from ctypes import c_bool, c_int32, POINTER


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
        self._boundary_mask = np.zeros(shape=shape, dtype=np.int32)
        self._boundary_value = np.zeros(shape=shape, dtype=self.numpy_dtype)

    def _op_invoke(self, depth: int):
        while len(self._data) < depth:
            self._data.append(
                np.zeros(shape=self.shape, dtype=self.numpy_dtype))
        self._data = self._data[:depth]

        np.roll(self._data, 1)

    @property
    def dimension(self):
        return len(self.shape)

    def serialize(self):
        boundary_mask = self._boundary_mask.ctypes.data_as(POINTER(c_int32))
        boundary_value = self._boundary_value.ctypes.data_as(
            POINTER(self.element.ctype))
        data = (POINTER(self.element.ctype) * len(self._data))(*
                                                               [data.ctypes.data_as(POINTER(self.element.ctype)) for data in self._data])

        return self.typing.ctype((c_int32 * self.dimension)(*self.shape),
                                 data,
                                 boundary_mask,
                                 boundary_value)

    @property
    def now(self):
        return self._data[0]

    def __getitem__(self, slice):
        return self.now[slice]

    def __setitem__(self, slice, value):
        self.now[slice] = value
