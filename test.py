from dataclasses import dataclass
from io import StringIO
import os
import random
import shutil
import time
from typing import Callable
import xgrid
from xgrid.util.console import Console
from xgrid.util.ffi import Compiler, Library
from xgrid.util.logging import Logger
from xgrid.util.typing.value import Floating


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

    test.log(f"execute grid kernel operator with index out of range, the program should run smoothly but with error message")


@test.fact("lang.Operator.grid_dot")
def operator_grid_dot() -> None:
    fmat = xgrid.grid[float, 2]

    @xgrid.kernel()
    def elementwise_mul(result: fmat, a: fmat, b: fmat) -> int:
        result[0, 0] = a[0, 0] * b[0, 0]
        return xgrid.shape(result, 0)

    SIZE = 100

    result = xgrid.Grid((SIZE, SIZE), float)
    a = xgrid.Grid((SIZE, SIZE), float)
    b = xgrid.Grid((SIZE, SIZE), float)

    for i in range(SIZE):
        for j in range(SIZE):
            a[i, j] = random.random()
            b[i, j] = random.random()

    assert elementwise_mul(result, a, b) == SIZE
    assert (result.now == a.now * b.now).all()


@test.fact("lang.Operator.grid_bounary")
def operator_grid_boundary() -> None:
    float2d = xgrid.grid[float, 2]

    @xgrid.kernel()
    def bounary_test(result: float2d, a: float2d, b: float2d) -> None:
        result[0, 0] = a[0, 0] * b[0, 0]
        with xgrid.boundary(result, 1):
            result[0, 0] = 3.0
    
    # print(bounary_test.src)


xgrid.init(comment=True, cacheroot=".xgridtest", indexguard=True, opt_level=2)
test.run()
