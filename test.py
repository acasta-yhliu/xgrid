from io import StringIO
import os
import shutil
import time
from typing import Callable
import xgrid.lang
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


@test.fact("lang.Operator")
def operator() -> None:
    def add(a: int, b: int) -> int:
        return a + b

    k = xgrid.lang.kernel(add)
    try:
        k()
    except Exception as e:
        raise e

    pass


# xgrid.init()

test.run()
