import sys
import astpretty
from ast import *

class InterpVisitor(NodeVisitor):
    "For gathering necessary information"

    def __init__(self):
        super(InterpVisitor, self).__init__()
        self.jump_kv = dict()
        self.ret_kv = dict()


    def visit_Call(self, node):
        func = node.func
        if isinstance(func, Name):
            if func.id == "transform_branch":
                kwds = node.keywords
                for kwd in kwds:
                    value = kwd.value
                    delattr(value, 'lineno')
                    delattr(value, 'col_offset')
                    self.jump_kv[kwd.arg] = value
            elif func.id == "transform_ret":
                kwds = node.keywords
                for kwd in kwds:
                    value = kwd.value
                    delattr(value, 'lineno')
                    delattr(value, 'col_offset')
                    self.ret_kv[kwd.arg] = value


class InterpTransformer(NodeTransformer):
    "For rewriting nodes"

    def __init__(self, jump_kv=dict(), ret_kv=dict()):
        super(InterpTransformer, self).__init__()
        self.jump_kv = jump_kv
        self.ret_kv = ret_kv

        # self.pc = pc # Name(id='pc', ctx=Load())
        # self.true_path = true_path # Name(id='target', ctx=Load())
        # self.false_path = false_path  # BinOp(left=Name(id='pc', ctx=Load()), op=Add(), right=Num(n=1))
        # self.cond = cond
        # self.entry_pc = entry_pc

    def visit_If(self, node):
        test = node.test
        body = node.body
        if isinstance(test, Call):
            if hasattr(test.func, 'id'):
                if test.func.id == "we_are_not_transformed":
                    kwds = test.keywords
                    assert len(kwds) == 1
                    kwd = kwds[0]
                    assert isinstance(kwd.value, Str)
                    if kwd.value.s == 'branch':
                        orig_body = node.body
                        new_if = If(test=Call(func=Name(id='we_are_jitted', ctx=Load()),
                                              args=[], keywords=[], starargs=None, kwargs=None),
                                    body=[self._create_jitted_jump_if(orig_body)],
                                    orelse=orig_body)
                        copy_location(new_if, node)
                        fix_missing_locations(new_if)
                        return new_if
                    elif kwd.value.s == 'ret':
                        orig_body = node.body
                        new_if = If(test=Call(func=Name(id='we_are_jitted', ctx=Load()),
                                              args=[], keywords=[], starargs=None, kwargs=None),
                                    body=[self._create_jitted_ret(orig_body)],
                                    orelse=orig_body)
                        copy_location(new_if, node)
                        fix_missing_locations(new_if)
                        return new_if
        self.generic_visit(node)
        return node

    def _create_jitted_jump_if(self, orig_body):
        jitted = \
            If(test=Call(func=self.jump_kv['cond'],
                         args=[], keywords=[], starargs=[], kwargs=None),
               body=[
                   Assign(targets=[Name(id='tstack', ctx=Store())],
                          value=Call(func=Name(id='t_push', ctx=Load()),
                                     args=[self.jump_kv['false_path'], Name(id='tstack', ctx=Load())],
                                     keywords=[], starargs=None, kwargs=None)),
                   Assign(targets=[Name(id=self.jump_kv['pc'].id, ctx=Store())],
                          value=self.jump_kv['true_path'])
               ],
               orelse=[
                   Assign(targets=[Name(id='tstack', ctx=Store())],
                          value=Call(func=Name(id='t_push', ctx=Load()),
                                     args=[self.jump_kv['true_path'], Name(id='tstack', ctx=Load())],
                                     keywords=[], starargs=None, kwargs=None)),
                   Assign(targets=[Name(id=self.jump_kv['pc'].id, ctx=Store())],
                          value=self.jump_kv['false_path'])
               ])
        return jitted

    def _create_jitted_ret(self, orig_body):
        return \
            If(test=Call(func=Name(id='t_is_empty', ctx=Load()),
                         args=[Name(id='tstack', ctx=Load())],
                         keywords=[], starargs=None, kwargs=None),
               body=[
                   Assign(targets=[Name(id='pc', ctx=Store())],
                          value=Call(func=Name(id='emit_ret', ctx=Load()),
                                     args=[Name(id='pc', ctx=Load()),
                                           self.ret_kv['ret_value']],
                                     keywords=[], starargs=None, kwargs=None)),
                   Expr(
                       value=Call(
                           func=Attribute(
                               value=Name(id='jitdriver', ctx=Load()),
                               attr='can_enter_jit',
                               ctx=Load()
                           ),
                           args=[],
                           keywords=[
                               keyword(arg='pc', value=self.ret_kv['pc']),
                               keyword(arg='bytecode', value=Name(id='bytecode', ctx=Load())),
                               keyword(arg='tstack', value=Name(id='tstack', ctx=Load())),
                               keyword(arg='self', value=Name(id='self', ctx=Load()))
                           ],
                           starargs=None, kwargs=None
                       )
                   )
               ],
               orelse=[
                   Assign(
                       targets=[Tuple(elts=[Name(id='pc', ctx=Store()),
                                            Name(id='tstack', ctx=Store())],
                                      ctx=Store())],
                       value=Call(
                           func=Attribute(value=Name(id='tstack', ctx=Load()),
                                          attr='t_pop', ctx=Load()),
                           args=[], keywords=[], starargs=None, kwargs=None
                       )
                   ),
                   Assign(
                       targets=[Name(id='pc', ctx=Store())],
                       value=Call(
                           func=Name(id='emit_jump', ctx=Load()),
                           args=[
                               Name(id='pc', ctx=Load()),
                               self.ret_kv['ret_value']
                           ],
                           keywords=[], starargs=None, kwargs=None
                       )
                   )
               ]
               )

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
        jump_kv = visitor.jump_kv
        ret_kv = visitor.ret_kv

        transformer = InterpTransformer(jump_kv=jump_kv, ret_kv=ret_kv)
        transformed = transformer.visit(tree)
        fix_missing_locations(transformed)
        print astunparse.unparse(transformed)
