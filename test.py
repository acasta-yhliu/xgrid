from xgrid.util.logging import Logger, LogLevel


class Test:
    def __init__(self, name: str) -> None:
        self.logger = Logger(name + ".test")
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
                self.logger.log(
                    LogLevel.Info, f"Test '{name}' started. ({self.executed}/{self.total})")
                try:
                    func(*args, **kwargs)
                    self.logger.log(LogLevel.Done, f"Test '{name}' passed.")
                    self.passed += 1
                except Exception as e:
                    self.logger.log(LogLevel.Fail, f"Test '{name}' failed.")
                    self.failed += 1
                    self.fail_case.append((name, e))
            return wrapped_func
        return decorator

    def summary(self):
        msg = [
            f"Summary: {self.total} tests, {self.passed} passed, {self.failed} failed"]
        if self.failed != 0:
            msg.append("The following case(s) have failed:")
            msg.extend(
                map(lambda x: f"  {x[0]} ({x[1].__class__.__name__})", self.fail_case))
        self.logger.log_multiln(
            LogLevel.Done if self.failed == 0 else LogLevel.Fail, msg)


test = Test("xgrid")


@test.case("addition")
def add(a: int, b: int) -> None:
    assert a + b == b + a


add(1, 2)

test.summary()
