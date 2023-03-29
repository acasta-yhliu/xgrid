class StubContext:
    def __enter__(self):
        pass

    def __exit__(self, a, b, c):
        pass


def c() -> StubContext:
    ...


def critical() -> StubContext:
    ...
