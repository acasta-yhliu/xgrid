from dataclasses import dataclass
from sys import stdout
from typing import TextIO

from xgrid.lang.ir import IR, Variable
from xgrid.lang.ir.expression import Expression, Signature, Terminal
from xgrid.util.console import ElementFormat, idfunc, idtype, idvar, kw, plain


@dataclass
class Statement(IR):
    def write(self, format: ElementFormat):
        pass


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

    def show(self, *, indent_size: int = 2, device: TextIO = stdout):
        format = ElementFormat()
        self.write(format)
        format.write(device)


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

    def write(self, format: ElementFormat):
        format.println(kw("while"), self.condition, kw("do"))
        with format.indent():
            format.print(*self.body)
        format.println(kw("end"))


@dataclass
class Evaluation(Statement):
    value: Expression

    def write(self, format: ElementFormat):
        format.println(kw("evaluate"), self.value)


@dataclass
class Assignment(Statement):
    terminal: Terminal
    value: Expression

    def write(self, format: ElementFormat):
        format.println(self.terminal, plain(":"), idtype(
            repr(self.terminal.type)), plain("="), self.value)


@dataclass
class Inline(Statement):
    source: str

    def write(self, format: ElementFormat):
        format.println(kw("inline"), kw("begin"))
        with format.indent():
            format.println(plain(self.source))
        format.println(kw("end"))


@dataclass
class For(Statement):
    variable: Variable
    start: Expression
    end: Expression
    step: Expression
    body: list[Statement]

    def write(self, format: ElementFormat):
        format.println(kw("for"), idvar("%" + self.variable.name), kw("in"),
                       self.start, plain(":"), self.end, plain(":"), self.step)
        with format.indent():
            format.print(*self.body)


@dataclass
class Boundary(Statement):
    variable: Variable
    mask: int
    body: list[Statement]

    def write(self, format: ElementFormat):
        format.println(kw("bounary"), plain(
            "("), self.variable, plain(","), plain(repr(self.mask)), plain(")"), kw("do"))
        with format.indent():
            format.print(*self.body)
        format.println(kw("end"))
