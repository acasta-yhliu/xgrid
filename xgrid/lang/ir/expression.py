from dataclasses import dataclass
from typing import Any

from xgrid.lang.ir import IR
from xgrid.util.console import ElementFormat
from xgrid.util.typing import BaseType


@dataclass
class Expression(IR):
    @property
    def type(self) -> BaseType:
        return BaseType()

    @property
    def value(self) -> Any:
        return None

    def write(self, format: ElementFormat):
        pass
