import xgrid.lang.ir as ir
import xgrid.lang.ir.statement as stat
import xgrid.lang.ir.expression as expr
from xgrid.lang.operator import Operator
from xgrid.util.console import LineFormat
from xgrid.util.ffi import Compiler, Library
from xgrid.util.logging import Logger
from xgrid.util.init import get_config
from xgrid.util.typing.reference import Pointer


class Generator:
    def __init__(self, operator: Operator) -> None:
        self.operator = operator
        assert self.operator.mode == "kernel"

        self.ir = operator.ir

        self.logger = Logger(self)

        self.predefine_code = LineFormat()
        self.code = LineFormat()

        self.config = get_config()

        self.generate()

    @property
    def native(self):
        return self.compile()

    @property
    def source(self):
        return repr(self.code)

    def generate(self):
        self.argtypes = [x[1] for x in self.ir.signature.arguments]
        self.rettype = self.ir.signature.return_type

        definition = f"{self.format_type()} {self.operator.name}()"

        self.predefine_code.println(definition + ";")

        self.code.println(definition + " {")
        with self.code.indent():
            self.visits(self.ir.body)
        self.code.println("}")

    def compile(self):
        self.logger.info(
            f"Compiling kernel {self.operator.name}' and retrive interface")
        # TODO: include predefine code
        dynlib = Compiler(cacheroot=self.config.cacheroot, cc=self.config.cc).compile(
            repr(self.code), self.config.cflags)
        return Library(dynlib).function(self.operator.name, self.argtypes, self.rettype)

    def visit(self, node: ir.IR):
        node_class = node.__class__.__name__
        method = getattr(self, "visit_" + node_class)
        return method(node)

    def visits(self, l: list[stat.Statement]):
        for item in l:
            self.visit(item)

    def visit_Return(self, ir: stat.Return):
        if ir.value is None:
            self.code.println(f"return;")
        else:
            self.code.println(f"return {self.visit(ir.value)};")

    def visit_Break(self, ir: stat.Break):
        self.code.println("break;")

    def visit_Continue(self, ir: stat.Continue):
        self.code.println("continue;")

    def visit_If(self, ir: stat.If):
        self.code.println(f"if ({self.visit(ir.condition)}) {{")
        with self.code.indent():
            self.visits(ir.body)
        if any(ir.orelse):
            self.code.println("} else {")
            with self.code.indent():
                self.visits(ir.orelse)
        self.code.println("}")

    def visit_While(self, ir: stat.While):
        self.code.println(f"while ({self.visit(ir.condition)}) {{")
        with self.code.indent():
            self.visits(ir.body)
        self.code.println("}")

    def visit_Evaluation(self, ir: stat.Evaluation):
        self.code.println(f"{self.visit(ir.value)};")

    def visit_Assignment(self, ir: stat.Assignment):
        # TODO
        pass

    def visit_Inline(self, ir: stat.Inline):
        self.code.println(ir.source)

    # ===== expression =====
    def visit_Binary(self, ir: expr.Binary):
        # TODO: handle case of is, nis, pow
        return f"({self.visit(ir.left)} {ir.operator.value} {self.visit(ir.right)})"

    def visit_Unary(self, ir: expr.Unary):
        return f"({ir.operator.value} {self.visit(ir.right)})"

    def visit_Condition(self, ir: expr.Condition):
        return f"({self.visit(ir.condition)} ? {self.visit(ir.body)} : {self.visit(ir.orelse)})"

    def visit_Constant(self, ir: expr.Constant):
        return repr(ir.value).lower()

    def visit_Identifier(self, ir: expr.Identifier):
        if isinstance(ir.variable.type, Pointer):
            return f"(*{ir.variable.name})"
        else:
            return ir.variable.name

    def visit_Access(self, ir: expr.Access):
        return f"({self.visit(ir.value)}).{ir.attribute}"

    def visit_Call(self, ir: expr.Call):
        return f"{ir.operator.name}({', '.join(map(self.visit, ir.arguments))})"

    # TODO: handle stencil
