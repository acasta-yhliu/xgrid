import ast
from functools import reduce
import inspect
import textwrap
from typing import Literal, NoReturn, cast
from struct import calcsize

from xgrid.lang.ir import Location, Variable
from xgrid.lang.ir.expression import Access, Binary, BinaryOperator, Call, Cast, Condition, Constant, Constructor, Expression, GridInfo, Identifier, Stencil, Terminal, Unary, UnaryOperator
from xgrid.lang.ir.statement import Assignment, Definition, Break, Continue, Evaluation, For, If, Inline, Return, Signature, While
from xgrid.util.init import get_config

from xgrid.util.logging import Logger
from xgrid.util.typing import BaseType, Void
from xgrid.util.typing.annotation import parse_annotation
from xgrid.util.typing.reference import Grid, Pointer, Reference
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
        ast.Div: BinaryOperator.Div,
        ast.Pow: BinaryOperator.Pow,
        ast.Mod: BinaryOperator.Mod,

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
    def __init__(self, func, name: str, mode: str, self_type: BaseType | None) -> None:
        self.logger = Logger(self)
        self.mode = mode
        self.func = func
        self.name = name

        self.self_type = self_type

        # extract source related information
        file = inspect.getsourcefile(func)
        self.file = "<unknown>" if file is None else file

        # extract source code of function
        lines, lineno = inspect.getsourcelines(func)

        source = textwrap.dedent(
            "\n".join(map(lambda x: textwrap.fill(x, tabsize=4, width=9999), lines)))

        ast_definition = ast.parse(source, self.file).body[0]
        ast.fix_missing_locations(ast_definition)
        ast.increment_lineno(ast_definition, lineno)

        self.context_stack = [mode]

        self.scope: dict[str, Variable] = {}
        self.boundary_mask = 0
        self.args: list[tuple[str, BaseType]] = []
        self.global_scope = func.__globals__
        self.global_scope.update({"int": int, "float": float, "bool": bool})

        self.includes = []

        self.ir = self.visit(ast_definition)

    @property
    def result(self):
        return self.ir

    @property
    def context(self):
        return self.context_stack[-1]

    def syntax_error(self, node: ast.AST, message: str) -> NoReturn:
        self.logger.dead(
            f"File {self.file}, line {node.lineno - 1}, in {self.name}",
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
        return Location(self.file, self.name, node.lineno - 1)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        sig = inspect.signature(self.func)
        for arg_name, arg_param in sig.parameters.items():
            assert arg_name == arg_param.name

            if arg_param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
                self.syntax_error(node,
                                  f"Argument '{arg_name}' of kind '{arg_param.kind}' is not supported")

            if arg_param.annotation == inspect.Parameter.empty and self.self_type is None:
                self.syntax_error(node,
                                  f"Argument '{arg_name}' requires type annotation")

            arg_type = self.self_type if arg_param.annotation == inspect.Parameter.empty else parse_annotation(
                arg_param.annotation, self.global_scope)

            if arg_type is None or isinstance(arg_type, Void):
                self.syntax_error(node,
                                  f"Argument '{arg_name}' requires non-void type annotation ({arg_param.annotation})")

            self.scope[arg_name] = Variable(arg_name, arg_type)  # type: ignore
            self.args.append((arg_name, arg_type))  # type: ignore

        ret_sig = parse_annotation(sig.return_annotation)
        if ret_sig is None or isinstance(ret_sig, Reference):
            self.syntax_error(node, f"Invalid return type '{ret_sig}'")
        self.return_type = ret_sig

        return Definition(self.location(node),
                          name=self.name,
                          mode=self.mode,
                          signature=Signature(self.args, self.return_type),
                          scope=self.scope,
                          body=[] if self.mode == "external" else self.visits(node.body))

    # ===== statements =====
    def visit_Return(self, node: ast.Return):
        return_value = None if node.value is None else self.visit(node.value)
        if return_value is not None:
            if return_value.type != self.return_type:
                self.syntax_error(
                    node, f"Incompatible return type '{return_value.type}' with '{self.return_type}'")
        return Return(self.location(node), return_value)

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

        self.context_stack.append("while")
        body = self.visits(node.body)
        # orelse = self.visits(node.orelse)
        if any(node.orelse):
            self.syntax_error(
                node, f"While statement does not support else clause")
        self.context_stack.pop()

        return While(self.location(node), condition, body)  # , orelse)

    def visit_Expr(self, node: ast.Expr):
        if self.context == "c":
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                docstring = node.value.value
                return Inline(self.location(node), docstring)
        else:
            return Evaluation(self.location(node), cast(Expression, self.visit(node.value)))

    def visit_With(self, node: ast.With):
        if len(node.items) != 1:
            self.syntax_error(node, "Only one pragma switch at once")

        withitem = node.items[0]

        if not isinstance(withitem.context_expr, ast.Call):
            self.syntax_error(
                node, f"Invalid pragma switch '{withitem.context_expr}'")
        global_obj = self.resolve_global(withitem.context_expr.func)
        import xgrid.lang as lang
        if global_obj == lang.c:
            self.context_stack.append("c")
            body = self.visits(node.body)
            self.context_stack.pop()
            return body
        elif global_obj == lang.boundary:
            args = withitem.context_expr.args
            if len(args) != 1 or not isinstance(args[0], ast.Constant) or type(args[0].value) != int:
                self.syntax_error(node, f"Invalid pragram switch 'boundary")

            boundary_mask = args[0].value
            self.boundary_mask = boundary_mask
            body = self.visits(node.body)
            self.boundary_mask = 0
            return body
        else:
            self.syntax_error(node, f"Unknown pragma switch '{global_obj}'")

    def visit_Assign(self, node: ast.Assign):
        location = self.location(node)
        value = cast(Expression, self.visit(node.value))
        if isinstance(value.type, Grid):
            self.syntax_error(node, f"Incompatible assignment to grid type")

        if len(node.targets) != 1:
            self.syntax_error(node, f"Multiple assignment is not supported")
        target = node.targets[0]

        terminal = self.resolve_local(target)

        # try to define new variable
        if terminal is None:
            if isinstance(target, ast.Name):
                variable = Variable(target.id, value.type)
                self.scope[target.id] = variable
                terminal = Identifier(
                    location, value.type, "load", variable)
            else:
                self.syntax_error(node, f"Undefined identifier {terminal}")

        if terminal.type != value.type:
            self.syntax_error(
                node, f"Incompatible assignment from type {value.type} to {terminal.type}")

        return Assignment(location, terminal, value)

    def visit_AugAssign(self, node: ast.AugAssign):
        value = cast(Expression, self.visit(node.value))
        target = self.resolve_local(node.target)
        if target is None:
            self.syntax_error(node, f"Undefined identifier {target}")

        optype = type(node.op)
        if optype not in OperatorMap.binary:
            self.syntax_error(
                node, f"Unsupported binary operator '{optype.__name__}'")
        binary_op = OperatorMap.binary[optype]

        if not isinstance(target.type, Number) or not isinstance(value.type, Number) or target.type != value.type:
            self.syntax_error(
                node, f"Incompatible binary operator '{binary_op.value}' with type '{target.type}' and '{value.type}'")

        if binary_op == BinaryOperator.Pow:
            return_type = Floating(64) if isinstance(
                target.type, Floating) and value.type.width_bits == 64 else Floating(32)
        else:
            return_type = target.type

        return Assignment(self.location(node), target, Binary(self.location(node), return_type, target, value, binary_op))

    def visit_For(self, node: ast.For):
        if not isinstance(node.target, ast.Name):
            self.syntax_error(
                node, f"For loop variable should be a name")

        # check whether is range or not
        iter_range = node.iter
        if not isinstance(iter_range, ast.Call) or not isinstance(iter_range.func, ast.Name) or iter_range.func.id != "range":
            self.syntax_error(node, f"For loop only supports range")

        args = iter_range.args
        if len(args) not in (2, 3):
            self.syntax_error(
                node, f"For loop requires start:end:step or start:end")

        loop_range: list[Expression] = list(map(self.visit, args))
        if len(loop_range) == 2:
            loop_range.append(Constant(self.location(node),
                              Integer(calcsize("i")), 1))

        # check type of loop range
        loop_range_type = loop_range[2].type
        for lr in loop_range:
            if lr.type != loop_range_type or not isinstance(lr.type, Number):
                self.syntax_error(
                    node, f"Incompatible loop range type '{lr.type}'")

        var_id = node.target.id
        if var_id not in self.scope:
            self.scope[var_id] = Variable(var_id, loop_range_type)

        loop_var = self.scope[var_id]
        if loop_var.type != loop_range_type:
            self.syntax_error(
                node, f"Incompatible loop variable type '{loop_var.type}' with range type '{loop_range_type}'")

        body = self.visits(node.body)
        return For(self.location(node), loop_var, loop_range[0], loop_range[1], loop_range[2], body)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.asname is not None:
                self.syntax_error(
                    node, f"Using import as include requires no alias for '{name.name}'")

            include_name = name.name.replace('.', '/')
            self.includes.append(include_name + ".h")

        return []

    # ===== expressions =====
    def parse_constant(self, node: ast.AST, constant):
        vtype = {int: Integer(calcsize("i")), float: Floating(get_config().fsize),
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

        if binary_op == BinaryOperator.Pow:
            return_type = Floating(calcsize("d")) if isinstance(
                left.type, Floating) and left.type.width_bits == 64 else Floating(get_config().fsize)
        else:
            return_type = left.type

        return Binary(self.location(node), return_type, left, right, binary_op)

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
        resolved_names = ["globals"]
        for attr in names:
            try:
                scope = scope[attr] if isinstance(
                    scope, dict) else getattr(scope, attr)
                resolved_names.append(attr)
            except KeyError:
                self.syntax_error(
                    node, f"Undefined attribute '{attr}' of '{'.'.join(resolved_names)}'")

        return scope

    def resolve_local(self, node: ast.AST) -> Terminal | None:
        location = self.location(node)

        if isinstance(node, ast.Subscript):
            def extract_space(grid: ast.Subscript, time_offset: int):
                # or self.context not in ("kernel", "critical", "boundary", "if"):
                if not isinstance(grid.value, ast.Name):
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

                spaces = []
                for space_slice in space_slices:
                    failed = False
                    value = 0
                    if isinstance(space_slice, ast.UnaryOp):
                        if type(space_slice.op) != ast.USub:
                            failed = True
                        else:
                            if not isinstance(space_slice.operand, ast.Constant) or type(space_slice.operand.value) != int:
                                failed = True
                            else:
                                value = -space_slice.operand.value
                    elif isinstance(space_slice, ast.Constant):
                        if type(space_slice.value) != int:
                            failed = True
                        else:
                            value = space_slice.value

                    if failed:
                        self.syntax_error(
                            grid, f"Incompatible subscript '{space_slice}'")
                    spaces.append(value)

                if len(spaces) != grid_var.type.dimension:
                    self.syntax_error(
                        grid, f"Incompatible subscript length '{len(spaces)}' with dimension {grid_var.type.dimension}")

                return Stencil(location, grid_var.type.element, ctx, grid_var, time_offset, spaces, self.boundary_mask)

            if isinstance(node.value, ast.Subscript):
                time_slice = node.slice
                if isinstance(time_slice, ast.Constant) and type(time_slice.value) == int:
                    time_offset = time_slice.value
                elif isinstance(time_slice, ast.UnaryOp) and type(time_slice.op) == ast.USub and isinstance(time_slice.operand, ast.Constant) and type(time_slice.operand.value) == int:
                    time_offset = -time_slice.operand.value
                else:
                    self.syntax_error(
                        node.value, f"Invalid time dimension subscript to '{node.value.__class__.__name__}")
                node = node.value
            else:
                time_offset = 0 if context(node.ctx) == "store" else -1

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
                t = variable.type.element if isinstance(
                    variable.type, Pointer) else variable.type
                return Identifier(self.location(node), t, context(node.ctx), variable)
            except KeyError:
                return None

        else:
            self.syntax_error(
                node, f"Python syntax '{node.__class__.__name__}' is currently unsupported")

    def visit_Name(self, node: ast.Name):
        local = self.resolve_local(node)
        return self.parse_constant(node, self.resolve_global(node)) if local is None else local

    def visit_Attribute(self, node: ast.Attribute):
        local = self.resolve_local(node)
        return self.parse_constant(node, self.resolve_global(node)) if local is None else local

    def visit_Subscript(self, node: ast.Subscript):
        return self.resolve_local(node)

    def visit_Call(self, node: ast.Call):
        from xgrid.lang.operator import Operator

        func_name = None
        self_type = None

        if isinstance(node.func, ast.Attribute) and (local_obj := self.resolve_local(node.func.value)) is not None:
            if isinstance(local_obj.type, Structure):
                func = getattr(
                    local_obj.type.dataclass, node.func.attr, None)
                func_name = f"{local_obj.type.dataclass.__qualname__}.{node.func.attr}"
                self_type = local_obj.type
            else:
                # fixed method call, in the future ?
                self.syntax_error(
                    node, f"Invalid method call on type {local_obj.type}")

            args: list[Expression] = [local_obj]
        else:
            func = self.resolve_global(node.func)
            args = []

        # specially handle cast expression
        if func == cast:
            if len(node.args) != 2:
                self.syntax_error(
                    node, f"Cast requires 2 arguments, got {len(node.args)}")
            target_type = parse_annotation(self.resolve_global(node.args[0]))
            if target_type is None:
                self.syntax_error(node, f"Invalid cast type")
            return Cast(self.location(node), target_type, self.visit(node.args[1]))

        args.extend(self.visit(i) for i in node.args)

        # specially handle type constructor
        if isinstance(func, type):
            internal_type = parse_annotation(func)
            if internal_type is None or not isinstance(internal_type, Structure):
                self.syntax_error(
                    node, f"Invalid type constructor '{func.__name__}'")

            func = Constructor(internal_type, Signature(
                list(internal_type.elements), internal_type))
            func_name = f"{internal_type.name}.constructor"

        # type check the function and arguments
        if not isinstance(func, Operator) and not isinstance(func, Constructor):
            # check the lazy method flag
            method_flag = getattr(func, "__xgrid_method", None)
            if method_flag is not None and self_type is not None:
                func = Operator(func, "function",
                                method_flag[0], method_flag[1], self_type)
            else:
                self.syntax_error(
                    node, f"Invalid call to object '{func}', it is not an operator")

        if func_name is None:
            func_name = func.name  # type: ignore

        if (expected := len(func.signature.arguments)) != len(args):
            self.syntax_error(
                node, f"Operator '{func_name}' requires {expected} arguments, but got {len(args)}")

        if isinstance(func, Operator) and func.mode == "external" and func.typecheck_override is not None:
            try:
                return_type = func.typecheck_override([i.type for i in args])
            except Exception as e:
                self.syntax_error(node, e.args[0])

            if func.name in ("shape", "dimension"):
                if not isinstance(args[0], Identifier):
                    self.syntax_error(
                        node, f"Incompatible '{func.name}' to argument '{args[0]}'")

                return GridInfo(self.location(node), Integer(calcsize("i")), cast(Literal["shape", "dimension"], func.name), args[0].variable, args[1] if func.name == "shape" else None)
        else:
            for id, (arg_name, arg_type) in enumerate(func.signature.arguments):
                if arg_type != args[id].type:
                    self.syntax_error(
                        node, f"Incompatible type '{args[id].type}' with '{arg_type}' of argument '{arg_name}, operator '{func_name}'")
            return_type = func.signature.return_type

        return Call(self.location(node), return_type, func, args)
