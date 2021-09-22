import pytest

import ast
import astunparse
import astpretty
from transform import *

def parse_and_dump(code):
    tree = ast.parse(code)
    visitor = InterpVisitor()
    visitor.visit(tree)

    transformer = InterpTransformer(visitor.jump_kv)

    # transformed = transformer.visit(tree)
    # fix_missing_locations(transformed)
    # astpretty.pprint(transformed)
    # print astunparse.unparse(transformed)


@pytest.mark.skip()
def test_construct_jitted_jump_if():
    cond_func = 'self.is_true'
    pc = 'pc'
    true_path = 'target'
    false_path = 'pc + 1'
    jitted_str = """
if we_are_jitted():
    if %s():
        tstack = t_push(%s, tstack)
        %s = %s
    else:
        tstack = t_push(%s, tstack)
        %s = %s
else:
    %s
    """ % (cond_func,
           false_path, pc, true_path,
           true_path, pc, false_path,
           'None')


@pytest.mark.skip()
def test_construct_jitted_ret():
    jitted_str = """
w_x = self.pop()
if we_are_jitted():
    if t_is_empty(tstack):
        pc = entry_state; self.restore_state()
        pc = emit_ret(pc, w_x)
        jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                pc=pc, tstack=tstack, self=self)
    else:
        pc, tstack = tstack.t_pop()
        pc = emit_ret(pc, w_x)
else:
    return w_x
"""
    tree = ast.parse(jitted_str)
    astpretty.pprint(tree)


def test_construct_jitted_jump():
    jitted_str = """
t = ord(bytecode[pc])
pc += 1
if we_are_jitted():
    if t_is_empty(tstack):
        pc = t
    else:
       pc, tstack = tstack.t_pop()
    pc = emit_jump(pc, t)
else:
    if t < pc:
        entry_state = t; self.save_state()
        jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                pc=t, tstack=tstack, self=self)
    pc = t
"""
    tree = ast.parse(jitted_str)
    astpretty.pprint(tree)


@pytest.mark.skip()
def test_parse_jump_if():
    branch = """
while True:
    opcode = bytecode[pc]
    pc += 1
    if opcode == JUMP_IF:
        target = ord(bytecode[pc])
        transform_branch(pc=pc,true_path=target,false_path=pc+1,cond=self.is_true,
                         entry_pc=target)
        if we_are_not_transformed():
            if self.is_true():
                if target < pc:
                    entry_state = target; self.save_state()
                    jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                            pc=target, tstack=tstack, self=self)

                pc = target
            else:
                pc += 1
"""

    exp = """
while True:
    opcode = bytecode[pc]
    if opcode == JUMP_IF:
        target = ord(bytecode[pc])
        transformer_jump(pc=pc,true_path=target,false_path=pc+1,cond=self.is_true)
        if we_are_jitted():
            if is_true():
                tstack = t_push(pc+1, tstack)
                pc = target
            else:
                tstack = t_push(target, tstack)
                pc = pc+1
        else:
            if self.is_true():
                if target < pc:
                    entry_state = target; self.save_state()
                    jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                            pc=target, tstack=tstack, self=self)

                pc = target
            else:
                pc += 1
"""
    parse_and_dump(branch)


def test_parse_ret():
    pass
