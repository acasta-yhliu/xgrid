import xgrid.lang.ir as ir
import xgrid.lang.ir.statement as stat
import xgrid.lang.ir.expression as expr
from xgrid.lang.operator import Operator
from xgrid.util.console import LineFormat
from xgrid.util.ffi import Compiler, Library
from xgrid.util.logging import Logger
from xgrid.util.init import get_config
from xgrid.util.typing import BaseType
from xgrid.util.typing.reference import Pointer


class Generator:
    def __init__(self, operator: Operator) -> None:
        self.operator = operator
        assert self.operator.mode == "kernel"

        self.logger = Logger(self)

        self.definitions = LineFormat()
        self.logger.info("Insert necessary and predefined headers")
        headers = ["stdio.h", "stdlib.h", "stdint.h"]
        for header in headers:
            self.definitions.println(f"#include <{header}>")
        self.definitions.println("")

        self.implementations: dict[str, LineFormat] = {}

        self.config = get_config()

        self.define_operator(operator)

    @property
    def native(self):
        return self.compile()

    @property
    def source(self):
        return repr(self.definitions) + "\n" + "\n".join(map(repr, self.implementations.values()))

    def format_type(self, t: BaseType):
        # TODO
        pass

    def define_operator(self, operator: Operator):
        if operator.name in self.implementations:
            return

        opir = operator.ir
        implementation = LineFormat()
        self.implementations[operator.name] = implementation

        arguments = ', '.join(
            map(lambda x: f"{self.format_type(x[1])} {x[0]}", opir.signature.arguments))
        definition = f"{self.format_type(opir.signature.return_type)} {operator.name}({arguments})"

        implementation.println(definition + "{")
        self.definitions.println(definition + ";")

        with implementation.indent():
            self.visits(operator.ir.body, implementation)
        implementation.println("}")

    def compile(self):
        self.logger.info(
            f"Compiling kernel {self.operator.name}' and retrive interface")
        dynlib = Compiler(cacheroot=self.config.cacheroot, cc=self.config.cc).compile(
            self.source, self.config.cflags)

        argtypes = [x[1] for x in self.operator.ir.signature.arguments]
        rettype = self.operator.ir.signature.return_type

        return Library(dynlib).function(self.operator.name, argtypes, rettype)

    def visit(self, node: ir.IR, implementation: LineFormat):
        node_class = node.__class__.__name__
        method = getattr(self, "visit_" + node_class)
        return method(node, implementation)

    def visits(self, l: list[stat.Statement], implementation: LineFormat):
        for item in l:
            self.visit(item, implementation)

    def visit_Return(self, ir: stat.Return, implementation: LineFormat):
        if ir.value is None:
            implementation.println(f"return;")
        else:
            implementation.println(
                f"return {self.visit(ir.value, implementation)};")

    def visit_Break(self, ir: stat.Break, implementation: LineFormat):
        implementation.println("break;")

    def visit_Continue(self, ir: stat.Continue, implementation: LineFormat):
        implementation.println("continue;")

    def visit_If(self, ir: stat.If, implementation: LineFormat):
        implementation.println(
            f"if ({self.visit(ir.condition, implementation)}) {{")
        with implementation.indent():
            self.visits(ir.body, implementation)
        if any(ir.orelse):
            implementation.println("} else {")
            with implementation.indent():
                self.visits(ir.orelse, implementation)
        implementation.println("}")

    def visit_While(self, ir: stat.While, implementation: LineFormat):
        implementation.println(
            f"while ({self.visit(ir.condition, implementation)}) {{")
        with implementation.indent():
            self.visits(ir.body, implementation)
        implementation.println("}")

    def visit_Evaluation(self, ir: stat.Evaluation, implementation: LineFormat):
        implementation.println(f"{self.visit(ir.value, implementation)};")

    def visit_Assignment(self, ir: stat.Assignment, implementation: LineFormat):
        implementation.println(
            f"{self.visit(ir.terminal, implementation)} = {self.visit(ir.value, implementation)};")

    def visit_Inline(self, ir: stat.Inline, implementation: LineFormat):
        implementation.println(ir.source)

    # ===== expression =====
    def visit_Binary(self, ir: expr.Binary, implementation: LineFormat):
        # TODO: handle case of is, nis, pow
        return f"({self.visit(ir.left, implementation)} {ir.operator.value} {self.visit(ir.right, implementation)})"

    def visit_Unary(self, ir: expr.Unary, implementation: LineFormat):
        return f"({ir.operator.value} {self.visit(ir.right, implementation)})"

    def visit_Condition(self, ir: expr.Condition, implementation: LineFormat):
        return f"({self.visit(ir.condition, implementation)} ? {self.visit(ir.body, implementation)} : {self.visit(ir.orelse, implementation)})"

    def visit_Constant(self, ir: expr.Constant, implementation: LineFormat):
        return repr(ir.value).lower()

    def visit_Identifier(self, ir: expr.Identifier, implementation: LineFormat):
        if isinstance(ir.variable.type, Pointer):
            return f"(*{ir.variable.name})"
        else:
            return ir.variable.name

    def visit_Access(self, ir: expr.Access, implementation: LineFormat):
        return f"({self.visit(ir.value, implementation)}).{ir.attribute}"

    def visit_Call(self, ir: expr.Call, implementation: LineFormat):
        return f"{ir.operator.name}({', '.join(map(lambda x: self.visit(x, implementation), ir.arguments))})"

    # TODO: handle stencil
