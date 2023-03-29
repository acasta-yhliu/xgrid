from dataclasses import dataclass

from xgrid.lang.ir import IR, Variable
from xgrid.lang.ir.expression import Expression
from xgrid.util.console import ElementFormat, idfunc, idtype, idvar, kw, plain
from xgrid.util.typing import BaseType


@dataclass
class Statement(IR):
    def write(self, format: ElementFormat):
        pass


@dataclass
class Signature:
    arguments: list[tuple[str, BaseType]]
    return_type: BaseType

    def __post_init__(self):
        self.argnames_map = dict(self.arguments)


@dataclass
class Definition(Statement):
    name: str
    mode: str
    signature: Signature
    scope: dict[str, Variable]
    body: list[Statement]

    def write(self, format: ElementFormat):
        args = [plain("(")]
        for name, type in self.signature.arguments:
            args.extend((idtype(repr(type)), idvar("%"+name)))
            args.append(plain(","))
        if any(args):
            args.pop()
        args.append(plain(")"))
        format.println(kw(self.mode), idtype(repr(self.signature.return_type)), idfunc(
            self.name), *args, kw("requires"))
        with format.indent():
            for name, var in self.scope.items():
                if name not in self.signature.argnames_map:
                    format.println(var, plain(":"), idtype(repr(var.type)))
        format.println(kw("begin"))
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
        with format.indent():
            format.println(plain(self.source))
        format.println(kw("end"))
