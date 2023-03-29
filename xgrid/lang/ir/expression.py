from dataclasses import dataclass
from enum import Enum
from typing import Literal

import xgrid.lang.operator as op
from xgrid.lang.ir import IR, Variable
from xgrid.util.console import ElementFormat, idconst, idfunc, kw, plain
from xgrid.util.typing import BaseType
from xgrid.util.typing.reference import Grid, Pointer


@dataclass
class Expression(IR):
    type: BaseType

    def write(self, format: ElementFormat):
        pass


class BinaryOperator(Enum):
    Add = "+"
    Sub = "-"
    Mul = "*"
    Div = "/"
    Pow = "^"
    Mod = "%"
    # Mat = "@"

    Is = "==="
    Nis = "!=="
    Eq = "=="
    Gt = ">"
    Ge = ">="
    Lt = "<"
    Le = "<="
    Neq = "!="

    And = "&&"
    Or = "||"

    def is_compare(self) -> bool:
        return self in (BinaryOperator.Is, BinaryOperator.Nis, BinaryOperator.Eq, BinaryOperator.Gt, BinaryOperator.Ge, BinaryOperator.Lt, BinaryOperator.Le, BinaryOperator.Neq)

    def is_logic(self) -> bool:
        return self in (BinaryOperator.And, BinaryOperator.Or)


class UnaryOperator(Enum):
    Pos = "+"
    Neg = "-"
    Not = "!"


@dataclass
class Binary(Expression):
    left: Expression
    right: Expression
    operator: BinaryOperator

    def write(self, format: ElementFormat):
        format.print(plain("("), self.left, plain(
            self.operator.value), self.right, plain(")"))


@dataclass
class Unary(Expression):
    right: Expression
    operator: UnaryOperator

    def write(self, format: ElementFormat):
        format.print(
            plain("("), plain(self.operator.value), self.right, plain(")"))


@dataclass
class Condition(Expression):
    condition: Expression
    body: Expression
    orelse: Expression

    def write(self, format: ElementFormat):
        format.print(plain("("), self.condition, plain("?"),
                     self.body, plain(":"), self.orelse, plain(")"))


@dataclass
class Constant(Expression):
    value: int | float | bool

    def write(self, format: ElementFormat):
        format.print(idconst(repr(self.value)))


@dataclass
class Terminal(Expression):
    context: Literal["load", "store"]


@dataclass
class Identifier(Terminal):
    variable: Variable

    def write(self, format: ElementFormat):
        if isinstance(self.variable.type, Pointer):
            format.print(kw("ref"))
        format.print(self.variable)


@dataclass
class Stencil(Terminal):
    variable: Variable
    critical: bool
    time_offset: int
    space_offset: list[int] | list[Expression]

    def __post_init__(self):
        assert isinstance(self.variable.type, Grid)

    def write(self, format: ElementFormat):
        offset = f"[{', '.join(map(str, self.space_offset))}][{self.time_offset}]"
        if self.critical:
            format.print(kw("stencil"), self.variable, plain(offset))
        else:
            format.print(self.variable, plain(offset))


@dataclass
class Access(Terminal):
    value: Terminal
    attribute: str

    def write(self, format: ElementFormat):
        format.print(self.value, plain(f".{self.attribute}"))


@dataclass
class Call(Expression):
    operator: "op.Operator"
    arguments: list[Expression]

    def write(self, format: ElementFormat):
        arglist = []
        for arg in self.arguments:
            arglist.append(arg)
            arglist.append(plain(","))
        if any(arglist):
            arglist.pop()
        format.print(idfunc(self.operator.name), plain(
            "("), *arglist, plain(")"))
