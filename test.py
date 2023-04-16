from dataclasses import dataclass
from io import StringIO
import os
import random
import shutil
import time
from typing import Callable

import numpy
import xgrid
from xgrid.util.console import Console
from xgrid.util.ffi import Compiler, Library
from xgrid.util.logging import Logger
from xgrid.util.typing.value import Floating
from matplotlib import pyplot, cm


class Test:
    def __init__(self) -> None:
        self.total = 0
        self.tests: list[tuple[str, Callable]] = []
        self.current_test = ""

    def fact(self, name: str):
        def decorator(func):
            self.tests.append((name, func))
        return decorator

    def log(self, msg: str):
        print("  \033[1minfo\033[0m:", self.current_test, msg)

    def run(self):
        def tmp_device():
            return StringIO(), StringIO()

        test_prompt = "\033[1;34mtest\033[0m: "

        total = len(self.tests)
        passed_cases: list[tuple[str, str, str]] = []
        failed_cases: list[tuple[str, tuple[Exception, str, str]]] = []

        total_begin_time = time.time()
        for id, (name, test) in enumerate(self.tests):
            test_id = f"{test_prompt}({id + 1}/{total}) {name}"
            print(test_id)

            out, err = tmp_device()
            Logger.stdouts[0] = Console(out)
            Logger.stderrs[0] = Console(err)

            self.current_test = name

            exc = None
            begin_time = time.time()
            try:
                test()
            except Exception as e:
                exc = e
            finally:
                end_time = time.time()
                print(
                    f"    \033[1;{'31mfailed' if exc else '32mpassed'}\033[0m in {(end_time - begin_time):.6f}s")
                out_msg, err_msg = out.read(), err.read()
                if exc:
                    raise exc
                    failed_cases.append((name, (exc, out_msg, err_msg)))
                else:
                    passed_cases.append((name, out_msg, err_msg))

        total_end_time = time.time()
        print(
            f"{test_prompt}total {total} tests, \033[1;32m{len(passed_cases)} passed\033[0m, \033[1;31m{len(failed_cases)} failed\033[0m in {total_end_time - total_begin_time:.5f} s")
        if any(failed_cases):
            print("    " + ", ".join(map(lambda x: x[0], failed_cases)))


test = Test()


@test.fact("ffi.Compiler")
def ffi_compiler() -> None:
    global lib_name

    cacheroot = ".xgridtest"

    if os.path.exists(f"./{cacheroot}"):
        test.log(f"remove existed cacheroot {cacheroot}")
        shutil.rmtree(f"./{cacheroot}", ignore_errors=True)

    cc = Compiler(cacheroot=".xgridtest", cc=["gcc", "clang"])

    assert os.path.exists(f"./{cacheroot}")
    assert cc.cc == "/usr/bin/gcc", "fetched wrong cc, expect /usr/bin/gcc"

    test.log(
        f"initialized compiler, cacheroot = {cc.cacheroot}, cc = {cc.cc}")

    simple_src = "#include <stdio.h>\n#include <stdbool.h>\n\nfloat universe(float a, float b) { return a + b; }\nvoid branch(bool a) { if(a) printf(\"branch function from c works fine\\n\"); }"

    cc.compile(simple_src)
    lib_name = cc.compile(simple_src)

    test.log(
        f"compiled source file without and with cached library to {lib_name}")

    dead_src = "innt main() {}"
    try:
        cc.compile(dead_src)
    except Exception as e:
        test.log("compiled source file with syntax error")


@test.fact("ffi.Library")
def ffi_library() -> None:
    global lib_name

    lib = Library(lib_name)

    test.log(f"library {lib_name} is loaded")

    float_add = lib.function(
        "universe", [Floating(4), Floating(4)], Floating(4))
    assert float_add(1.2, 2.3) == 3.5
    test.log(f"fetched and tested dynamic function 'float universe(float, float)'")


TEMP = 10


@test.fact("lang.Operator.simple")
def operator_simple() -> None:
    @xgrid.kernel()
    def aux(a: int, b: int) -> int:
        return a + b + TEMP

    a = random.randint(0, 1000)
    b = random.randint(0, 1000)
    test.log(
        f"execute simple kernel operator, should obtain (a := {a}) + (b := {b}) + (TEMP := 10)")
    assert aux(a, b) == a + b + TEMP


@dataclass
class Vector3i:
    x: int
    y: int
    z: int

    @xgrid.function(method=True)
    def dot(self, b: "Vector3i") -> int:
        return self.x * b.x + self.y * b.y + self.z * b.z


@test.fact("lang.Operator.structure")
def operator_structure() -> None:
    @xgrid.kernel()
    def aux(a: Vector3i, b: Vector3i) -> int:
        return a.dot(b)

    a = Vector3i(random.randint(0, 1000), random.randint(
        0, 1000), random.randint(0, 1000))
    b = Vector3i(random.randint(0, 1000), random.randint(
        0, 1000), random.randint(0, 1000))
    test.log(f"execute structure kernel operator, should obtain {a} dot {b}")
    assert aux(a, b) == a.dot(b)


@test.fact("lang.Operator.grid")
def operator_grid() -> None:
    @xgrid.kernel()
    def aux(a: xgrid.grid[int, 2]) -> None:
        a[0, 0] = 4

    grid = xgrid.Grid((10, 10), dtype=int)
    aux(grid)

    test.log(f"execute grid kernel operator, should give 4 to each elements")
    for a in grid.now:
        for element in a:
            assert element == 4


@test.fact("lang.Operator.grid_indexguard")
def operator_grid_indexguard() -> None:
    @xgrid.kernel()
    def aux(a: xgrid.grid[int, 2]) -> None:
        a[0, 0] = a[-1, -1][-1]

    grid = xgrid.Grid((10, 10), dtype=int)
    aux(grid)

    test.log(f"execute grid kernel operator with index out of range, the program should run smoothly without error message")


def initial_convection_1d(x: xgrid.Grid, dx):
    x.now.fill(1)
    x.now[int(.5 / dx):int(1 / dx + 1)] = 2
    x.boundary[0] = 1


@test.fact("lang.Operator.convection_1d")
def operator_convection_1d() -> None:
    float1d = xgrid.grid[float, 1]

    nx = 41
    dx = 2 / (nx - 1)
    nt = 25
    dt = .025
    c = 1

    u = xgrid.Grid((nx,), float)
    initial_convection_1d(u, dx)

    @xgrid.kernel()
    def convection_1d(u: float1d, c: float, dt: float, dx: float) -> None:
        u[0] = u[0] - c * dt / dx * (u[0] - u[-1])
        with xgrid.boundary(u, 1):
            u[0] = 1.0

    for _ in range(nt):
        convection_1d(u, c, dt, dx)

    pyplot.plot(numpy.linspace(0, 2, nx), u.now)
    pyplot.savefig(f"convection_1d.png")
    pyplot.close()


@test.fact("lang.Operator.convection_1d_nonlinear")
def operator_convection_1d_nonlinear() -> None:
    float1d = xgrid.grid[float, 1]

    nx = 41
    dx = 2 / (nx - 1)
    nt = 10
    dt = .025

    u = xgrid.Grid((nx,), float)
    initial_convection_1d(u, dx)

    @xgrid.kernel()
    def convection_1d(u: float1d, dt: float, dx: float) -> None:
        u[0] = u[0] - u[0] * dt / dx * (u[0] - u[-1])
        with xgrid.boundary(u, 1):
            u[0] = 1.0

    for _ in range(nt):
        convection_1d(u, dt, dx)

    pyplot.plot(numpy.linspace(0, 2, nx), u.now)
    pyplot.savefig(f"convection_1d_nonlinear.png")
    pyplot.close()


@test.fact("lang.Operator.diffusion_1d")
def operator_diffusion() -> None:
    float1d = xgrid.grid[float, 1]

    nx = 41
    dx = 2 / (nx - 1)
    nt = 20
    dt = .01
    nu = 0.01

    u = xgrid.Grid((nx,), float)
    u.now.fill(1)
    u.now[int(.5 / dx):int(1 / dx + 1)] = 2
    u.boundary[0] = u.boundary[-1] = 1

    @xgrid.kernel()
    def diffusion_1d(u: float1d, nu: float, dt: float, dx: float) -> None:
        u[0] = u[0] + nu * dt / dx ** 2.0 * (u[1] - 2.0 * u[0] + u[-1])
        with xgrid.boundary(u, 1):
            u[0] = 1.0

    for _ in range(nt):
        diffusion_1d(u, nu, dt, dx)

    pyplot.plot(numpy.linspace(0, 2, nx), u.now)
    pyplot.savefig(f"diffusion_1d.png")
    pyplot.close()


@test.fact("lang.Operator.convection_2d")
def operator_convection_2d() -> None:
    float2d = xgrid.grid[float, 2]

    nx = ny = 201
    dx = 2 / (nx-1)
    dy = 2 / (ny-1)
    c = 1
    sigma = .5  # from the CLF condition
    dt = sigma * (dx / c) * 0.1
    nt = int(.7/dt)

    u = xgrid.Grid((nx, ny), float)
    u.now.fill(1)
    u.now[int(0.5/dx):int(1/dx) + 1, int(0.5/dy):int(1/dy) + 1] = 2
    u.boundary[0, :] = u.boundary[:, 0] = 1

    @xgrid.kernel()
    def convection_2d(u: float2d, c: float, dt: float, dx: float, dy: float) -> None:
        cdx = c * dt / dx
        cdy = c * dt / dy
        u[0, 0] = u[0, 0] + cdx * \
            (u[0, 0] - u[-1, 0]) - cdy * (u[0, 0] - u[0, -1])
        with xgrid.boundary(u, 1):
            u[0, 0] = 1.0

    for _ in range(nt):
        convection_2d(u, c, dt, dx, dy)

    pyplot.imshow(u.now)
    pyplot.savefig("convection_2d.png")
    pyplot.close()

# @test.fact("lang.Operator.cavity_flow")
# def operator_cavity_flow() -> None:
#     float2d = xgrid.grid[float, 2]

#     @xgrid.kernel()
#     def cavity(u: float2d, v: float2d, p: float2d, b: float2d, rho: float, nu: float, dt: float, dx: float, dy: float) -> None:
#         b[0, 0] = (rho * (1.0 / dt *
#                           ((u[0, 1] - u[0, -1]) /
#                            (2.0 * dx) + (v[1, 0] - v[-1, 0]) / (2.0 * dy)) -
#                           ((u[0, 1] - u[0, -1]) / (2.0 * dx))**2.0 -
#                           2.0 * ((u[1, 0] - u[-1, 0]) / (2.0 * dy) *
#                                  (v[0, 1] - v[0, -1]) / (2.0 * dx)) -
#                           ((v[1, 0] - v[-1, 0]) / (2.0 * dy))**2.0))

#         for _ in range(0, 50):
#             p[0, 0] = (((p[0, 1] + p[0, -1]) * dy**2.0 +
#                         (p[1, 0] + p[-1, 0]) * dx**2.0) /
#                        (2.0 * (dx**2.0 + dy**2.0)) -
#                        dx**2.0 * dy**2.0 / (2.0 * (dx**2.0 + dy**2.0)) *
#                        b[0, 0][0])

#             with xgrid.boundary(p, 1):
#                 p[0, 0] = p[0, -1][0]  # dp/dx = 0 at x = 2
#             with xgrid.boundary(p, 2):
#                 p[0, 0] = p[1, 0][0]   # dp/dy = 0 at y = 0
#             with xgrid.boundary(p, 3):
#                 p[0, 0] = p[0, 1][0]   # dp/dx = 0 at x = 0
#             with xgrid.boundary(p, 4):
#                 p[0, 0] = 0.0

#             xgrid.tick(p)

#         xgrid.tick(p)

#         u[0, 0] = (u[0, 0] -
#                    u[0, 0] * dt / dx *
#                    (u[0, 0] - u[0, -1]) -
#                    v[0, 0] * dt / dy *
#                    (u[0, 0] - u[-1, 0]) -
#                    dt / (2.0 * rho * dx) * (p[0, 1][0] - p[0, -1][0]) +
#                    nu * (dt / dx**2.0 *
#                          (u[0, 1] - 2.0 * u[0, 0] + u[0, -1]) +
#                          dt / dy**2.0 *
#                          (u[1, 0] - 2.0 * u[0, 0] + u[-1, 0])))

#         v[0, 0] = (v[0, 0] -
#                    u[0, 0] * dt / dx *
#                    (v[0, 0] - v[0, -1]) -
#                    v[0, 0] * dt / dy *
#                    (v[0, 0] - v[-1, 0]) -
#                    dt / (2.0 * rho * dy) * (p[1, 0][0] - p[-1, 0][0]) +
#                    nu * (dt / dx**2.0 *
#                          (v[0, 1] - 2.0 * v[0, 0] + v[0, -1]) +
#                          dt / dy**2.0 *
#                          (v[1, 0] - 2.0 * v[0, 0] + v[-1, 0])))

#         with xgrid.boundary(u, 1):
#             u[0, 0] = 0.0

#         with xgrid.boundary(u, 2):
#             u[0, 0] = 1.0

#         with xgrid.boundary(v, 1):
#             v[0, 0] = 0.0

#     FRAMES = 100

#     SIZE_X = SIZE_Y = 41

#     u = xgrid.Grid((SIZE_X, SIZE_Y), float)
#     v = xgrid.Grid((SIZE_X, SIZE_Y), float)
#     p = xgrid.Grid((SIZE_X, SIZE_Y), float)
#     b = xgrid.Grid((SIZE_X, SIZE_Y), float)

#     u.boundary[0, :] = 1
#     u.boundary[:, 0] = 1
#     u.boundary[:, -1] = 1
#     u.boundary[-1, :] = 2

#     v.boundary[0, :] = 1
#     v.boundary[-1, :] = 1
#     v.boundary[:, 0] = 1
#     v.boundary[:, -1] = 1

#     p.boundary[:, -1] = 1
#     p.boundary[0, :] = 2
#     p.boundary[:, 0] = 3
#     p.boundary[-1, :] = 4

#     b.boundary[0, :] = 1
#     b.boundary[-1, :] = 1
#     b.boundary[:, 0] = 1
#     b.boundary[:, -1] = 1

#     for _ in range(FRAMES):
#         cavity(u, v, p, b, 1.0, 0.1, 0.001,
#                2 / (SIZE_X - 1), 2 / (SIZE_Y - 1))

#     x = numpy.linspace(0, 2, SIZE_X)
#     y = numpy.linspace(0, 2, SIZE_Y)
#     X, Y = numpy.meshgrid(x, y)

#     pyplot.contourf(X, Y, p.now, alpha=0.5)
#     pyplot.colorbar()
#     pyplot.contour(X, Y, p.now)
#     pyplot.streamplot(X, Y, u.now, v.now)
#     pyplot.xlabel('X')
#     pyplot.ylabel('Y')

#     filename = "cavity.png"
#     test.log(f"exporting png image file to {filename}")
#     pyplot.savefig(filename)


xgrid.init(comment=True, cacheroot=".xgridtest",
           opt_level=3, precision="double")
test.run()
