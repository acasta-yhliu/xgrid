from dataclasses import fields

from xgrid.lang.ir import IR


class IRVisitor:
    def __init__(self) -> None:
        pass

    def generic_visit(self, ir: IR):
        ir_fields = fields(ir)
        for ir_field in ir_fields:
            ir_fval = getattr(ir, ir_field.name)
            if isinstance(ir_fval, list):
                for val in ir_fval:
                    self.visit(val)
            else:
                self.visit(ir_fval)

    def visit(self, ir: IR):
        if isinstance(ir, IR):
            ir_class = ir.__class__.__name__
            method = getattr(self, "visit_" + ir_class, None)
            if method is None:
                self.generic_visit(ir)
            else:
                method(ir)
