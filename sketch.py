import ctypes

point = type("Point", (ctypes.Structure,), {"_fields_": [
         ("x", ctypes.c_int32), ("y", ctypes.c_int32)]})

point_something = point(1, 2)
print(point_something.x)