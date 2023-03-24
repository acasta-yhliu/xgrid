from dataclasses import dataclass
from enum import Enum
from typing import Literal

from xgrid.lang.ir import IR, Variable
from xgrid.util.console import ElementFormat, const, plain


@dataclass
class Expression(IR):
    @property
    def type(self):
        return getattr(self, "_type")

    def write(self, format: ElementFormat):
        pass


class BinaryOperator(Enum):
    Add = "+"
    Sub = "-"
    Mul = "*"
    Div = "/"
    Pow = "^"
    Mod = "%"

    Eq = "=="
    Gt = ">"
    Ge = ">="
    Lt = "<"
    Le = "<="
    Neq = "!="

    And = "&&"
    Or = "||"


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
        format.print(const(repr(self.value)))


@dataclass
class Access(Expression):
    variable: Variable
    context: Literal["load", "store"]

    def write(self, format: ElementFormat):
        format.print(self.variable)
