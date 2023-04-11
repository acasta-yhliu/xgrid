import ctypes

class Test(ctypes.Structure):
    _fields_ = [("test", ctypes.POINTER(ctypes.c_int32))]

a = Test((ctypes.c_int32 * 3)(1, 2, 3))

print(a.test)