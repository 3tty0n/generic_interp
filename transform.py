import sys

from ast import *

class InterpVisitor(NodeVisitor):
    "For gathering necessary information"

    def __init__(self):
        super(InterpVisitor, self).__init__()
        self.pc = None
        self.true_path = None
        self.false_path = None
        self.cond = None

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, Name):
            if func.id == "transformer":
                kwds = node.keywords
                for kwd in kwds:
                    if kwd.arg == "pc":
                        value = kwd.value
                        delattr(value, 'lineno')
                        delattr(value, 'col_offset')
                        self.pc = value
                    elif kwd.arg == "true_path":
                        value = kwd.value
                        delattr(value, 'lineno')
                        delattr(value, 'col_offset')
                        self.true_path = value
                    elif kwd.arg == "false_path":
                        value = kwd.value
                        delattr(value, 'lineno')
                        delattr(value, 'col_offset')
                        self.false_path = value
                    elif kwd.arg == "cond":
                        value = kwd.value
                        delattr(value, 'lineno')
                        delattr(value, 'col_offset')
                        self.cond = value


class InterpTransformer(NodeTransformer):
    "For rewriting nodes"

    def __init__(self, pc, true_path, false_path, cond):
        super(InterpTransformer, self).__init__()
        self.pc = pc # Name(id='pc', ctx=Load())
        self.true_path = true_path # Name(id='target', ctx=Load())
        self.false_path = false_path  # BinOp(left=Name(id='pc', ctx=Load()), op=Add(), right=Num(n=1))
        self.cond = cond

    def visit_If(self, node):
        test = node.test
        if isinstance(test, Call):
            if hasattr(test.func, 'id'):
                if test.func.id == "we_are_not_transformed":
                    orig_body = node.body
                    new_if = If(test=Call(func=Name(id='we_are_jitted', ctx=Load()),
                                          args=[], keywords=[], starargs=None, kwargs=None),
                                body=[self._create_jitted_body(orig_body)],
                                orelse=orig_body)
                    copy_location(new_if, node)
                    fix_missing_locations(new_if)
                    return new_if
        self.generic_visit(node)
        return node

    def _create_jitted_body(self, orig_body):
        jitted = \
            If(test=Call(func=self.cond,
                         args=[], keywords=[], starargs=[], kwargs=None),
               body=[
                   Assign(targets=[Name(id='tstack', ctx=Store())],
                          value=Call(func=Name(id='t_push', ctx=Load()),
                                     args=[self.false_path, Name(id='tstack', ctx=Load())],
                                     keywords=[], starargs=None, kwargs=None)),
                   Assign(targets=[Name(id=self.pc.id, ctx=Store())],
                          value=self.true_path)
               ],
               orelse=[
                   Assign(targets=[Name(id='tstack', ctx=Store())],
                          value=Call(func=Name(id='t_push', ctx=Load()),
                                     args=[self.true_path, Name(id='tstack', ctx=Load())],
                                     keywords=[], starargs=None, kwargs=None)),
                   Assign(targets=[Name(id=self.pc.id, ctx=Store())],
                          value=self.false_path)
               ])
        return jitted

if __name__ == '__main__':
    import astunparse

    if len(sys.argv) < 2:
        print "Usage: %s filename" % (sys.argv[0])
        exit(1)
    fname = sys.argv[1]
    with open(fname) as f:
        tree = parse(f.read())
        visitor = InterpVisitor()
        visitor.visit(tree)

        transformer = InterpTransformer(
            pc=visitor.pc, true_path=visitor.true_path,
            false_path=visitor.false_path, cond=visitor.cond)
        transformed = transformer.visit(tree)
        print astunparse.unparse(transformed)
