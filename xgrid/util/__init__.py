from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")


def eager_map(func: Callable[[T], Any], elements: Iterable[T] | list[T]) -> None:
    for ele in elements:
        func(ele)


def join(l):
    result = []
    for item in l:
        if item is not None:
            if isinstance(item, list):
                result.extend(flatten(item))
            else:
                yield item
