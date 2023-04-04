from xgrid.lang.ir import IR


class IRVisitor:
    def __init__(self) -> None:
        pass

    def generic_visit(self, ir: IR):
        ...

    def visit(self, ir: IR):
        ir_class = ir.__class__.__name__
        method = getattr(self, "visit_" + ir_class, None)
        if method is None:
            return self.generic_visit(ir)
        else:
            return method(ir)
