from io import StringIO
import xgrid.lang.ir as ir
import xgrid.lang.ir.statement as stat
import xgrid.lang.ir.expression as expr
from xgrid.lang.ir.visitor import IRVisitor
from xgrid.lang.operator import Operator
from xgrid.util.console import LineFormat
from xgrid.util.ffi import Compiler, Library
from xgrid.util.logging import Logger
from xgrid.util.init import get_config
from xgrid.util.typing import BaseType
from xgrid.util.typing.reference import Grid, Pointer
from xgrid.util.typing.value import Boolean, Floating, Integer, Structure


class StencilParser(IRVisitor):
    def __init__(self, ir: list[ir.IR]) -> None:
        super().__init__()
        self.ir = ir

    def dimension_var(self, dimension: int):
        return f"$dim{dimension}"


class Generator:
    def __init__(self, operator: Operator) -> None:
        self.operator = operator
        assert self.operator.mode == "kernel"

        self.logger = Logger(self)
        self.config = get_config()

        self.definitions = LineFormat()
        self.logger.info("Insert necessary and predefined headers")
        headers = ["stdio.h", "stdlib.h", "stdint.h", "stdbool.h", "math.h"]
        if self.config.parallel:
            headers.append("omp.h")

        for header in headers:
            self.definitions.println(f"#include <{header}>")

        for header in operator.includes:
            self.definitions.println(f"#include \"{header}\"")

        self.op_impls: dict[str, LineFormat] = {}
        self.t_impls: dict[str, LineFormat] = {}

        self.define_operator(operator)

    @property
    def native(self):
        return self.compile()

    @property
    def source(self):
        with StringIO() as io:
            self.definitions.write(io)
            for impls in self.t_impls.values():
                impls.write(io)

            for impls in self.op_impls.values():
                impls.write(io)
            return io.getvalue()

    def format_type(self, t: BaseType, abbr: bool = False):
        if isinstance(t, Boolean):
            return "b" if abbr else "bool"
        elif isinstance(t, Integer):
            return f"i{t.width_bits}" if abbr else f"int{t.width_bits}_t"
        elif isinstance(t, Floating):
            fullname = {32: "float", 64: "double"}[t.width_bits]
            return fullname[0] if abbr else fullname
        elif isinstance(t, Structure):
            self.define_type(t, t.name)
            return f"st{t.name}" if abbr else f"struct {t.name}"

        # reference type does not have abbr
        elif isinstance(t, Pointer):
            return f"{self.format_type(t.element)}*"
        elif isinstance(t, Grid):
            name = f"__Grid{t.dimension}d_{self.format_type(t.element, True)}"
            self.define_type(t, name)
            return f"struct {name}"

    def define_type(self, t: BaseType, name: str):
        if name in self.t_impls:
            return

        self.definitions.println(f"struct {name};")
        implementation = LineFormat()
        self.t_impls[name] = implementation
        implementation.println(f"struct {name} {{")

        if isinstance(t, Structure):
            with implementation.indent():
                for name, type in t.elements:
                    implementation.println(f"{self.format_type(type)} {name};")
            implementation.println("};")
        elif isinstance(t, Grid):
            with implementation.indent():
                implementation.println("int32_t time_idx, time_ttl;")
                implementation.println(f"int32_t shape[{t.dimension}];")
                implementation.println(
                    f"{self.format_type(t.element)}** data;")
            implementation.println("};")

    def define_operator(self, operator: Operator):
        if operator.name in self.op_impls:
            return

        opir = operator.ir
        implementation = LineFormat()
        self.op_impls[operator.name] = implementation

        arguments = ', '.join(
            map(lambda x: f"{self.format_type(x[1])} {x[0]}", opir.signature.arguments))
        definition = f"{self.format_type(opir.signature.return_type)} {operator.name}({arguments})"
        self.definitions.println(
            ("extern " if operator.mode == "external" else "") + definition + ";")

        if operator.mode == "external":
            return

        implementation.println(definition + "{")

        with implementation.indent():
            for name, var in operator.ir.scope.items():
                if name not in operator.signature.argnames_map:
                    implementation.println(
                        f"{self.format_type(var.type)} {name};")

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
        if self.config.comment and isinstance(node, stat.Statement):
            implementation.println(
                f"#line {node.location.line} \"{node.location.file}\"", indent=False)
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
        if ir.operator == expr.BinaryOperator.Pow:
            if isinstance(ir.type, Floating) and ir.type.width_bits == 64:
                pow_func = "pow"
            else:
                pow_func = "powf"
            return f"{pow_func}({self.visit(ir.left, implementation)}, {self.visit(ir.right, implementation)})"
        else:
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
        args = []

        for id, argument in enumerate(ir.arguments):
            arg_code = self.visit(argument, implementation)
            arg_type = ir.operator.signature.arguments[id][1]
            if isinstance(arg_type, Pointer) and argument.type == arg_type.element:
                arg_code = f"&{arg_code}"
            args.append(arg_code)
        args = ', '.join(args)
        if isinstance(ir.operator, expr.Constructor):
            return f"(({self.format_type(ir.operator.type)}) {{{args}}})"
        else:
            self.define_operator(ir.operator)
            return f"{ir.operator.name}({args})"

    def visit_Cast(self, ir: expr.Cast, implementation: LineFormat):
        return f"(({self.format_type(ir.type)})({self.visit(ir.value, implementation)}))"

    def visit_Stencil(self, ir: expr.Stencil, implementation: LineFormat):
        return "<stencil>"
    # TODO: handle stencil
