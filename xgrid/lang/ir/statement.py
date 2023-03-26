from dataclasses import dataclass

from xgrid.lang.ir import IR, Variable
from xgrid.lang.ir.expression import Expression
from xgrid.util.console import ElementFormat, idtype, kw, plain


@dataclass
class Statement(IR):
    def write(self, format: ElementFormat):
        pass


@dataclass
class Definition(Statement):
    name: str
    mode: str
    body: list[Statement]

    def write(self, format: ElementFormat):
        format.println(kw(self.mode), plain(self.name), kw("begin"))
        with format.indent():
            format.print(*self.body)
        format.println(kw("end"))


@dataclass
class Return(Statement):
    value: Expression | None

    def write(self, format: ElementFormat):
        format.println(kw("return"), plain(
            "") if self.value is None else self.value)


@dataclass
class Break(Statement):
    def write(self, format: ElementFormat):
        format.println(kw("break"))


@dataclass
class Continue(Statement):
    def write(self, format: ElementFormat):
        format.println(kw("continue"))


@dataclass
class If(Statement):
    condition: Expression
    body: list[Statement]
    orelse: list[Statement]

    def write(self, format: ElementFormat):
        format.println(kw("if"), self.condition, kw("do"))
        with format.indent():
            format.print(*self.body)
        if any(self.orelse):
            format.println(kw("else"))
            with format.indent():
                format.print(*self.orelse)
        format.println(kw("end"))


@dataclass
class While(Statement):
    condition: Expression
    body: list[Statement]
    orelse: list[Statement]

    def write(self, format: ElementFormat):
        format.println(kw("while"), self.condition, kw("do"))
        with format.indent():
            format.print(*self.body)
        if any(self.orelse):
            format.println(kw("else"))
            with format.indent():
                format.print(*self.orelse)
        format.println(kw("end"))


@dataclass
class Evaluation(Statement):
    value: Expression

    def write(self, format: ElementFormat):
        format.println(kw("evaluate"), self.value)


@dataclass
class Assignment(Statement):
    variable: Variable
    value: Expression

    def write(self, format: ElementFormat):
        format.println(self.variable, plain(":"), idtype(
            repr(self.variable.type)), plain("="), self.value)


@dataclass
class Inline(Statement):
    source: str

    def write(self, format: ElementFormat):
        format.println(kw("inline"), kw("begin"))
        format.print(plain(self.source))
        format.println(kw("end"))
