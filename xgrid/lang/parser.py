import ast
import inspect
from itertools import chain
import textwrap
from typing import Literal
from xgrid.lang.ir import Definition, Location
from xgrid.lang.ir.statement import Return

from xgrid.util.logging import Logger


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

        self.context: str = mode
        self.ir = self.visit(ast_definition)

    @property
    def result(self):
        return self.ir

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

    def location(self, node: ast.AST):
        return Location(self.file, self.func_name, node.lineno - 1)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # extract annotation

        # extract body
        body = list(chain(map(self.visit, node.body)))

        return Definition(self.location(node), self.func_name)

    # ===== statements =====
    def visit_Return(self, node: ast.Return):
        return [Return(self.location(node), None if node.value is None else self.visit(node.value))]

    def visit_Pass(self, node: ast.Pass):
        return []

    def visit_Break(self, node: ast.Break):
        return [Break(self.location(node))]