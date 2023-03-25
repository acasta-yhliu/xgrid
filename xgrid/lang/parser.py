import ast
from functools import reduce
import inspect
from itertools import chain
import textwrap
from typing import cast
from xgrid.lang.ir import Definition, Location
from xgrid.lang.ir.expression import Binary, BinaryOperator, Condition, Constant, Expression, Unary, UnaryOperator
from xgrid.lang.ir.statement import Break, Continue, Evaluation, If, Return, While

from xgrid.util.logging import Logger
from xgrid.util.typing.value import Boolean, Floating, Integer, Number, Value


class OperatorMap:
    unary: dict[type[ast.unaryop], UnaryOperator] = {
        ast.UAdd: UnaryOperator.Pos,
        ast.USub: UnaryOperator.Neg,
        ast.Not: UnaryOperator.Not
    }

    binary: dict[type[ast.operator | ast.cmpop | ast.boolop], BinaryOperator] = {
        ast.Add: BinaryOperator.Add,
        ast.Sub: BinaryOperator.Sub,
        ast.Mult: BinaryOperator.Mul,
        # ast.MatMult: BinaryOperator.Mat,
        ast.Div: BinaryOperator.Div,
        ast.Pow: BinaryOperator.Pow,
        ast.Mod: BinaryOperator.Mod,

        ast.Is: BinaryOperator.Is,
        ast.IsNot: BinaryOperator.Nis,
        ast.Eq: BinaryOperator.Eq,
        ast.NotEq: BinaryOperator.Neq,
        ast.Gt: BinaryOperator.Gt,
        ast.GtE: BinaryOperator.Ge,
        ast.Lt: BinaryOperator.Lt,
        ast.LtE: BinaryOperator.Le,

        ast.And: BinaryOperator.And,
        ast.Or: BinaryOperator.Or
    }


class Parser:
    def __init__(self, func, mode: str) -> None:
        self.logger = Logger(self)

        # extract source related information
        file = inspect.getsourcefile(func)
        self.file = "<unknown>" if file is None else file

        self.func_name = func.__name__

        # extract source code of function
        lines, lineno = inspect.getsourcelines(func)

        source = textwrap.dedent(
            "\n".join(map(lambda x: textwrap.fill(x, tabsize=4, width=9999), lines)))

        ast_definition = ast.parse(source, self.file).body[0]
        ast.fix_missing_locations(ast_definition)
        ast.increment_lineno(ast_definition, lineno)

        self.context_stack = [mode]
        self.ir = self.visit(ast_definition)

    @property
    def result(self):
        return self.ir

    @property
    def context(self):
        return self.context_stack[-1]

    def syntax_error(self, node: ast.AST, message: str):
        self.logger.dead(
            f"File {self.file}, line {node.lineno - 1}, in {self.func_name}",
            f"  Syntax error: {message}")

    def visit(self, node: ast.AST):
        node_class = node.__class__.__name__
        method = getattr(self, "visit_" + node_class, None)
        if method is None:
            self.syntax_error(node,
                              f"Python syntax '{node_class}' is currently unsupported")
        else:
            return method(node)

    def visits(self, l: list[ast.stmt]):
        return list(chain.from_iterable(map(self.visit, l)))  # type: ignore

    def location(self, node: ast.AST):
        return Location(self.file, self.func_name, node.lineno - 1)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # extract annotation

        # extract body
        body = self.visits(node.body)  # type: ignore

        return Definition(self.location(node), self.func_name)

    # ===== statements =====
    def visit_Return(self, node: ast.Return):
        return Return(self.location(node), None if node.value is None else self.visit(node.value))

    def visit_Pass(self, node: ast.Pass):
        return []

    def visit_Break(self, node: ast.Break):
        return Break(self.location(node))

    def visit_Continue(self, node: ast.Continue):
        return Continue(self.location(node))

    def visit_If(self, node: ast.If):
        condition = cast(Expression, self.visit(node.test))

        self.context_stack.append("if")
        body = self.visits(node.body)
        orelse = self.visits(node.orelse)
        self.context_stack.pop()

        return If(self.location(node), condition, body, orelse)

    def visit_While(self, node: ast.While):
        condition = cast(Expression, self.visit(node.test))

        self.context_stack.append("if")
        body = self.visits(node.body)
        orelse = self.visits(node.orelse)
        self.context_stack.pop()

        return While(self.location(node), condition, body, orelse)

    def visit_Expr(self, node: ast.Expr):
        return Evaluation(self.location(node), cast(Expression, self.visit(node.value)))

    # ===== expressions =====
    def visit_Constant(self, node: ast.Constant):
        if type(node.value) not in (int, float, bool):
            self.syntax_error(node, f"Invalid constant value '{node.value}'")
        vtype = {int: Integer(0), float: Floating(0),
                 bool: Boolean()}[node.value]
        return Constant(self.location(node), vtype, node.value)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        optype = type(node.op)
        if optype not in OperatorMap.unary:
            self.syntax_error(
                node, f"Unsupported unary operator '{optype.__name__}'")
        unary_op = OperatorMap.unary[optype]

        right = cast(Expression, self.visit(node.operand))
        if (unary_op == UnaryOperator.Not and not isinstance(right.type, Boolean)) or (unary_op in (UnaryOperator.Pos, UnaryOperator.Neg) and not isinstance(right.type, Number)):
            self.syntax_error(
                node, f"Incompatible unary operator '{unary_op.value}' with type '{right.type}'")

        return Unary(self.location(node), right.type, right, unary_op)

    def visit_BinOp(self, node: ast.BinOp):
        optype = type(node.op)
        if optype not in OperatorMap.binary:
            self.syntax_error(
                node, f"Unsupported binary operator '{optype.__name__}'")
        binary_op = OperatorMap.binary[optype]

        left = cast(Expression, self.visit(node.left))
        right = cast(Expression, self.visit(node.right))
        if not isinstance(left.type, Number) or not isinstance(right.type, Number) or left.type != right.type:
            self.syntax_error(
                node, f"Incompatible binary operator '{binary_op.value}' with type '{left.type}' and '{right.type}'")

        return Binary(self.location(node), left.type, left, right, binary_op)

    def visit_BoolOp(self, node: ast.BoolOp):
        location = self.location(node)
        op = OperatorMap.binary[type(node.op)]
        values = [cast(Expression, self.visit(i)) for i in node.values]
        for value in values:
            if not isinstance(value.type, Boolean):
                self.syntax_error(
                    node, f"Incompatible boolean operator '{op.value}' with '{value.type}'")
        return reduce(lambda x, y: Binary(location, Boolean(), x, y, op), values)

    def visit_Compare(self, node: ast.Compare):
        location = self.location(node)
        left = cast(Expression, self.visit(node.left))
        if not isinstance(left.type, Number):
            self.syntax_error(
                node, f"Incompatible compare expression with type '{left.type}'")

        comparators = [cast(Expression, self.visit(i))
                       for i in node.comparators]
        ops = [OperatorMap.binary[type(i)] for i in node.ops]

        for i, comparator in enumerate(comparators):
            if comparator.type != left.type:
                self.syntax_error(
                    node, f"Incompatible compare operator '{ops[i].value}' with type '{left.type}' and '{comparator.type}'")

        boolean = Boolean()
        return reduce(lambda x, y: Binary(location, boolean, x, y, BinaryOperator.And),
                      [Binary(location, boolean, left, comparators[i], ops[i]) for i in range(len(ops))])

    def visit_IfExp(self, node: ast.IfExp):
        condition = cast(Expression, self.visit(node.test))
        if not isinstance(condition.type, Boolean):
            self.syntax_error(
                node, f"Incompatible condition type '{condition.type}' of if expression")
        body = cast(Expression, self.visit(node.body))
        orelse = cast(Expression, self.visit(node.orelse))
        if body.type != orelse.type or not isinstance(body.type, Value):
            self.syntax_error(
                node, f"Incompatible type '{body.type}' and '{orelse.type}' of if expression")
        return Condition(self.location(node), body.type, condition, body, orelse)

    def visit_Name(self, node: ast.Name):
        return self.resolve_name(node.id, node.ctx, [])

    def visit_Subscript(self, node: ast.Subscript):
        if self.context not in ("kernel", "critical"):
            self.syntax_error(
                node, f"Incompatible subscript under context '{self.context}'")

        critical = self.context == "kernel-critical"
