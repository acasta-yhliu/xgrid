from dataclasses import dataclass

from xgrid.lang.ir import IR
from xgrid.util.console import ElementFormat, Foreground


@dataclass
class Expression(IR):
    def write(self, format: ElementFormat):
        format.print("<expression>", None, Foreground.red)
