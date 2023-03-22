from dataclasses import dataclass

from xgrid.lang.ir import IR
from xgrid.lang.ir.expression import Expression
from xgrid.util import eager_map
from xgrid.util.console import Foreground, ElementFormat


@dataclass
class Statement(IR):
    def write(self, format: ElementFormat):
        format.begin().print("<statement>", None, Foreground.red).end()


@dataclass
class Return(Statement):
    value: Expression

    def write(self, format: ElementFormat):
        format.begin().print("return", None, Foreground.blue).space().print(self.value).end()


@dataclass
class Break(Statement):
    def write(self, format: ElementFormat):
        format.begin().print("break", None, Foreground.blue).end()


@dataclass
class Continue(Statement):
    def write(self, format: ElementFormat):
        format.begin().print("continue", None, Foreground.blue).end()


@dataclass
class If(Statement):
    condition: Expression
    true_branch: list[Statement]
    false_branch: list[Statement]

    def write(self, format: ElementFormat):
        format.begin().print("if", None, Foreground.blue).space().print(
            self.condition).space().print("do", None, Foreground.blue).end()
        with format.indent():
            eager_map(format.print, self.true_branch)
        if any(self.false_branch):
            format.begin().print("else", None, Foreground.blue).end()
            with format.indent():
                eager_map(format.print, self.false_branch)
        format.begin().print("end", None, Foreground.blue).end()
