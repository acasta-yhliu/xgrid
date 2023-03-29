import ast
from functools import reduce
import inspect
import textwrap
from typing import NoReturn, cast
from struct import calcsize

from xgrid.lang.ir import Location, Variable
from xgrid.lang.ir.expression import Access, Binary, BinaryOperator, Condition, Constant, Expression, Identifier, Stencil, Terminal, Unary, UnaryOperator
from xgrid.lang.ir.statement import Definition, Break, Continue, Evaluation, If, Inline, Return, While

from xgrid.util.logging import Logger
from xgrid.util.typing.reference import Grid
from xgrid.util.typing.value import Boolean, Floating, Integer, Number, Structure, Value


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


def context(ctx: ast.expr_context):
    if type(ctx) == ast.Load:
        return "load"
    else:
        return "store"


class Parser:
    def __init__(self, func, mode: str) -> None:
        self.logger = Logger(self)
        self.mode = mode

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

        self.scope: dict[str, Variable] = {}
        self.global_scope = func.__globals__

        self.ir = self.visit(ast_definition)

    @property
    def result(self):
        return self.ir

    @property
    def context(self):
        return self.context_stack[-1]

    def syntax_error(self, node: ast.AST, message: str) -> NoReturn:
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
        result = []
        for item in l:
            visited = self.visit(item)
            if isinstance(visited, list):
                result.extend(visited)
            else:
                result.append(visited)
        return result

    def location(self, node: ast.AST):
        return Location(self.file, self.func_name, node.lineno - 1)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # TODO: extract annotation

        # extract body
        return Definition(self.location(node),
                          name=self.func_name,
                          mode=self.mode,
                          body=self.visits(node.body))

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
        if self.context == "c":
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                docstring = node.value.value
                return Inline(self.location(node), docstring)
        else:
            return Evaluation(self.location(node), cast(Expression, self.visit(node.value)))

    def visit_With(self, node: ast.With):
        for withitem in node.items:
            withitem.context_expr

    # TODO: for loop, assign statement

    # ===== expressions =====
    def parse_constant(self, node: ast.AST, constant):
        vtype = {int: Integer(calcsize("i")), float: Floating(calcsize("f")),
                 bool: Boolean()}
        if type(constant) not in vtype:
            self.syntax_error(
                node, f"Incompatible constant '{constant}' of type '{type(constant)}'")
        return Constant(self.location(node), vtype[type(constant)], constant)

    def visit_Constant(self, node: ast.Constant):
        return self.parse_constant(node, node.value)

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

    def resolve_global(self, node: ast.AST):
        names = []
        while True:
            if isinstance(node, ast.Name):
                names.append(node.id)
                break
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
                node = node.value
            else:
                self.syntax_error(
                    node, f"Python syntax '{node.__class__.__name__}' is currently unsupported")

        names.reverse()

        scope = self.global_scope
        resolved_names = []
        for attr in names:
            try:
                scope = scope[attr] if isinstance(
                    scope, dict) else getattr(scope, attr)
                resolved_names.append(attr)
            except KeyError:
                self.syntax_error(
                    node, f"Undefined attribute '{attr}' of '{'.'.join(resolved_names)}'")

        return scope

    def resolve_local(self, node: ast.AST, create_type: Value | None = None, create_name: str = "") -> Terminal | None:
        location = self.location(node)

        if isinstance(node, ast.Subscript):
            def extract_space(grid: ast.Subscript, time_offset: int):
                if not isinstance(grid.value, ast.Name) or self.context not in ("kernel", "critical"):
                    self.syntax_error(
                        grid, f"Incompatible subscript to '{grid.value.__class__.__name__}' under context '{self.context}'")

                if grid.value.id not in self.scope:
                    self.syntax_error(
                        grid, f"Undefined identifier '{grid.value.id}'")

                grid_var = self.scope[grid.value.id]
                if not isinstance(grid_var.type, Grid):
                    self.syntax_error(
                        grid, f"Incompatible subscript to type '{grid_var.type}'")

                location = self.location(grid)
                ctx = context(grid.ctx)

                if isinstance(grid.slice, ast.Tuple):
                    space_slices = grid.slice.elts
                else:
                    space_slices = [grid.slice]

                critical = self.context == "critical"
                spaces = []
                for space_slice in space_slices:
                    if critical:
                        space_index = cast(Expression, self.visit(space_slice))
                        if not isinstance(space_index.type, Integer):
                            self.syntax_error(
                                grid, f"Incompatible subscript type '{space_index.type}'")
                        spaces.append(space_index)
                    else:
                        if not isinstance(space_slice, ast.Constant) or type(space_slice.value) != int:
                            self.syntax_error(
                                grid, f"Incompatible subscript '{space_slice}'")
                        spaces.append(space_slice.value)

                return Stencil(location, grid_var.type.element, ctx, grid_var, critical, time_offset, spaces)

            if isinstance(node.value, ast.Subscript):
                time_slice = node.slice
                if not isinstance(time_slice, ast.Constant) or type(time_slice.value) != int:
                    self.syntax_error(
                        node.value, f"Invalid time dimension subscript to '{node.value.__class__.__name__}")
                time_offset = time_slice.value
            else:
                time_offset = 0

            return extract_space(node, time_offset)

        elif isinstance(node, ast.Attribute):
            value = self.resolve_local(node.value)

            if value is None or not isinstance(value.type, Structure) or node.attr not in value.type.elements_map:
                return None
            else:
                return Access(location, value.type.elements_map[node.attr], context(node.ctx), value, node.attr)

        elif isinstance(node, ast.Name):
            try:
                variable = self.scope[node.id]
                return Identifier(self.location(node), variable.type, context(node.ctx), variable)
            except KeyError:
                if create_type is not None:
                    variable = Variable(create_name, create_type)
                    self.scope[node.id] = variable
                    return Identifier(self.location(node), create_type, context(node.ctx), variable)
                else:
                    return None

        else:
            self.syntax_error(
                node, f"Python syntax '{node.__class__.__name__}' is currently unsupported")

    def visit_Name(self, node: ast.Name):
        local = self.resolve_local(node)
        return self.resolve_global(node) if local is None else local

    def visit_Attribute(self, node: ast.Attribute):
        local = self.resolve_local(node)
        return self.resolve_global(node) if local is None else local

    def visit_Subscript(self, node: ast.Subscript):
        return self.resolve_local(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            local_obj = self.resolve_local(node.func.value)
            if local_obj is not None:
                # TODO: method call to local object
                pass

        global_function = self.resolve_global(node.func)
