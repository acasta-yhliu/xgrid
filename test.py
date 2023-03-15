from io import StringIO
import os
import shutil
from typing import Callable
from xgrid.util.console import Console
from xgrid.util.ffi import Compiler
from xgrid.util.logging import Logger


class Test:
    def __init__(self) -> None:
        self.total = 0
        self.tests: list[tuple[str, Callable]] = []

    def fact(self, name: str):
        def decorator(func):
            self.tests.append((name, func))
        return decorator

    def run(self):
        def tmp_device():
            return StringIO(), StringIO()

        test_prompt = "  \033[1mtest\033[0m: "

        total = len(self.tests)
        passed_cases: list[tuple[str, str, str]] = []
        failed_cases: list[tuple[str, tuple[Exception, str, str]]] = []

        for id, (name, test) in enumerate(self.tests):
            test_id = f"{test_prompt}({id + 1}/{total}) '{name}'"
            print(f"{test_id} begin.")

            out, err = tmp_device()
            Logger.stdouts[0] = Console(out)
            Logger.stderrs[0] = Console(err)

            exc = None
            try:
                test()
            except Exception as e:
                exc = e
            finally:
                print(f"{test_id} {'failed' if exc else 'passed'}")
                out_msg, err_msg = out.read(), err.read()
                if exc:
                    failed_cases.append((name, (exc, out_msg, err_msg)))
                else:
                    passed_cases.append((name, out_msg, err_msg))

        print(
            f"{test_prompt}total {total} tests, \033[1m{len(passed_cases)} passed\033[0m, \033[1m{len(failed_cases)} failed\033[0m.")
        if any(failed_cases):
            print(f"{test_prompt}failed cases are:")
            print("    " + ", ".join(map(lambda x: x[0], failed_cases)))
            failed_dict = dict(failed_cases)
            while True:
                print(f"{test_prompt}input id to check more information: ", end="")
                id = input()
                if id.startswith("."):
                    if id == ".list":
                        print(
                            "    " + ", ".join(map(lambda x: x[0], failed_cases)))
                    elif id == ".exit":
                        break
                    else:
                        print(f"{test_prompt}unknown command '{id}'")
                else:
                    if id in failed_dict:
                        exc, out_msg, err_msg = failed_dict[id]
                        print(exc, out_msg, err_msg)
                    else:
                        print(f"{test_prompt}unknown test '{id}'.")


test = Test()


@test.fact("ffi")
def jitdriver() -> None:
    # remove existing file
    cacheroot = ".xgridtest"

    if os.path.exists(f"./{cacheroot}"):
        shutil.rmtree(f"./{cacheroot}", ignore_errors=True)

    jit = Compiler(cacheroot=".xgridtest", cc=["gcc", "clang"])

    assert os.path.exists(f"./{cacheroot}")
    assert jit.cc == "/usr/bin/gcc", "fetched wrong cc, expect /usr/bin/gcc"

    simple_src = "# include<stdio.h>\nint main(int argc, char** argv) { printf(\"Hello World\\n\"); }"

    jit.compile(simple_src)
    jit.compile(simple_src)

    dead_src = "innt main() {}"
    try:
        jit.compile(dead_src)
    except:
        pass


test.run()
