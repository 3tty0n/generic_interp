from rpython.rlib import jit, threadedcode
from rpython.rlib.threadedcode import we_are_not_transformed

jitdriver = jit.JitDriver(greens=['pc', 'bytecode'],
                          reds=['self'])

transformer = threadedcode.Transformer(pc='pc')

class Frame(object):

    def __init__(self, bytecode):
        self.bytecode = bytecode
        self.stack = [None] * 8
        self.stackpos = 0

        self.saved_stack = [None] * 8
        self.saved_stackpos = 0

    @jit.not_in_trace
    def save_state(self):
        self.saved_stackpos = self.stackpos
        for i in range(len(self.stack)):
            self.saved_stack[i] = self.stack[i]

    @jit.not_in_trace
    def restore_state(self):
        for i in range(len(self.stack)):
            self.stack[i] = self.saved_stack[i]
        self.stackpos = self.saved_stackpos

    @jit.dont_look_inside
    def push(self, w_x):
        self.stack[self.stackpos] = w_x
        self.stackpos += 1

    @jit.dont_look_inside
    def pop(self):
        stackpos = self.stackpos - 1
        assert stackpos >= 0
        self.stackpos = stackpos
        res = self.stack[stackpos]
        self.stack[stackpos] = None
        return res

    @jit.dont_look_inside
    def drop(self, n):
        for _ in range(n):
            self.pop()

    @jit.dont_look_inside
    def is_true(self):
        w_x = self.pop()
        res = w_x.is_true()
        return res

    @jit.dont_look_inside
    def CONST_INT(self, pc):
        if isinstance(pc, int):
            x = ord(self.bytecode[pc])
            self.push(W_IntObject(x))
        else:
            raise OperationError

    @jit.dont_look_inside
    def ADD(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.add(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def SUB(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.sub(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MUL(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mul(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DIV(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MOD(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mod(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DUP(self):
        w_x = self.pop()
        self.push(w_x)
        self.push(w_x)

    @jit.dont_look_inside
    def LT(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.lt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def GT(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.gt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def EQ(self):
        w_y = self.pop()
        w_x = self.pop()
        self.push(w_x.eq(w_y))

    @jit.dont_look_inside
    def NE(self):
        w_y = self.pop()
        w_x = self.pop()
        if w_x.eq(w_y).intvalue:
            self.push(W_IntObject(1))
        else:
            self.push(W_IntObject(0))

    @jit.dont_look_inside
    def RETURN(self):
        return self.pop()

    @jit.dont_look_inside
    def CALL(self, t):
        res = self.interp(t)
        if res is not None:
            self.push(res)

    @jit.dont_look_inside
    def RET(self, n):
        self.drop(n-1)
        return self.pop()

    def interp(self, pc=0):
        tstack = t_empty()
        entry_state = 0
        bytecode = self.bytecode

        while pc < len(bytecode):
            jitdriver.jit_merge_point(bytecode=bytecode, entry_state=entry_state,
                                      tstack=tstack, pc=pc, self=self)
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self.CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self.pop()

            elif opcode == DUP:
                self.DUP()

            elif opcode == LT:
                self.LT()

            elif opcode == EQ:
                self.EQ()

            elif opcode == ADD:
                self.ADD()

            elif opcode == SUB:
                self.SUB()

            elif opcode == DIV:
                self.DIV()

            elif opcode == MUL:
                self.MUL()

            elif opcode == MOD:
                self.MOD()

            elif opcode == CALL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL(t)

            elif opcode == RET:
                argnum = ord(bytecode[pc])
                pc += 1
                return self.RET(argnum)

            elif opcode == JUMP:
                t = ord(bytecode[pc])
                pc += 1
                transformer.can_enter_tier1_jump(pc=pc, target=t)
                if we_are_in_tier2(kind='jump'):
                    if t < pc:
                        jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                pc=t, tstack=tstack, self=self)
                        pc = t
                        # if we_are_jitted():
                        #     if t_is_empty(tstack):
                        #         entry_state = pc; self.save_state()
                        #         if t < pc:
                        #             jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                        #                                     pc=t, tstack=tstack, self=self)
                        #         pc = t
                        #     else:
                        #         pc, tstack = tstack.t_pop()
                        #     pc = emit_jump(pc, t)
                        # else:
                        #     if t < pc:
                        #         entry_state = t; self.save_state()
                        #         jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                        #                                 pc=t, tstack=tstack, self=self)
                        #     pc = t

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                transformer.can_enter_tier1_branch(pc=pc, true_path=target,
                                                   false_path=pc+1, cond=self.is_true,
                                                   entry_pc=target)
                if we_are_in_tier2(kind='branch'):
                    if self.is_true():
                        if target < pc:
                            entry_state = target; self.save_state()
                            jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                    pc=target, tstack=tstack, self=self)

                        pc = target
                    else:
                        pc += 1

                # if we_are_jitted():
                #     if self.is_true():
                #         pc += 1
                #         tstack = t_push(pc, tstack)
                #         pc = target
                #     else:
                #         tstack = t_push(target, tstack)
                #         pc += 1
                # else:
                #     if self.is_true():
                #         if target < pc:
                #             entry_state = target; self.save_state()
                #             jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                #                                     pc=target, tstack=tstack, self=self)

                #         pc = target
                #     else:
                #         pc += 1

            elif opcode == EXIT:
                w_x = self.pop()
                transformer.can_enter_tier1_ret(pc=pc, ret_value=w_x)
                if we_are_in_tier2(kind='ret'):
                    return w_x

                # if we_are_jitted():
                #     if t_is_empty(tstack):
                #         w_x = self.pop()
                #         # pc = entry_state;  self.restore_state()
                #         pc = emit_ret(pc, w_x)
                #         jitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                #                                 pc=pc, tstack=tstack, self=self)
                #     else:
                #         pc, tstack = tstack.t_pop()
                #         w_x = self.pop()
                #         pc = emit_ret(pc, w_x)
                # else:
                #     return w_x

            else:
                assert False, 'Unknown opcode: %d' % opcode
