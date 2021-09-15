import ast
import astunparse
import astpretty
from transform import *


def construct_jitted_jump_if():
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


def parse_and_dump(code):
    tree = ast.parse(code)
    visitor = InterpVisitor()
    visitor.visit(tree)

    transformer = InterpTransformer(
        pc=visitor.pc, true_path=visitor.true_path,
        false_path=visitor.false_path, cond=visitor.cond)
    transformed = transformer.visit(tree)
    # pprint(transformed)
    print astunparse.unparse(transformed)


def test_parse():
    branch = """
while True:
    opcode = bytecode[pc]
    pc += 1
    if opcode == JUMP_IF:
        target = ord(bytecode[pc])
        transformer(pc=pc,true_path=target,false_path=pc+1,cond=self.is_true)
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
        transformer(pc=pc,true_path=target,false_path=pc+1,cond=self.is_true)
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
