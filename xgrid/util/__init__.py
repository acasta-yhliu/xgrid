from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")


def eager_map(func: Callable[[T], Any], elements: Iterable[T] | list[T]) -> None:
    for ele in elements:
        func(ele)

