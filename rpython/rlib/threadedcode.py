class Transformer(object):
    def __init__(self, pc=None):
        self.pc = pc

    def transform_jump(self, cond, true_path, false_path, **kwargs):
        return None

    def transform_ret(self, ret_value, **kwargs):
        return None

    def transform_branch(self, cond, true_path, false_path, **kwargs):
        return None

def we_are_not_transformed(kind):
    return True
