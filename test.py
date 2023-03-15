import os
import shutil
from xgrid.util.ffi import Jit


class Test:
    def __init__(self, name: str) -> None:
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.executed = 0
        self.fail_case: list[tuple[str, Exception]] = []

    def case(self, name: str):
        self.total += 1

        def decorator(func):
            def wrapped_func(*args, **kwargs):
                self.executed += 1
                progress = f"({self.executed}/{self.total})"
                print(f" > Test{progress} '{name}' started.")
                try:
                    func(*args, **kwargs)
                    print(f" > Test{progress} '{name}' passed.")
                    self.passed += 1
                except Exception as e:
                    print(f" > Test {progress} '{name}' failed.")
                    self.failed += 1
                    self.fail_case.append((name, e))
            return wrapped_func
        return decorator

    def summary(self):
        ignore = self.total - self.passed - self.failed
        msg = [
            f"Test summary: {self.total} tests, {self.passed} passed, {self.failed} failed, {ignore} ignore."]
        if self.failed != 0:
            msg.append("The following case(s) have failed:")
            msg.extend(
                map(lambda x: f"  {x[0]} ({x[1].__class__.__name__})", self.fail_case))

        for line in msg:
            print(" > " + line)


test = Test("xgrid")


@test.case("addition")
def add(a: int, b: int) -> None:
    assert a + b == b + a


add(1, 2)


@test.case("ffi")
def jitdriver(name: str) -> None:
    # remove existing file
    if os.path.exists(f"./.{name}"):
        shutil.rmtree(f"./.{name}", ignore_errors=True)

    jit = Jit(name)

    assert os.path.exists(f"./.{name}")
    assert jit.cc == "/usr/bin/gcc"
    
    simple_src = "# include<stdio.h>\nint main(int argc, char** argv) { printf(\"Hello World\\n\"); }"

    jit.compile(simple_src)
    jit.compile(simple_src)

    dead_src = "innt main() {}"
    try:
        jit.compile(dead_src)
    except:
        pass

jitdriver("tmptest")

test.summary()
