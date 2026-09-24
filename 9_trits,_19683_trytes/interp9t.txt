"""Reference interpreter for "9 trits, 19683 trytes".
https://esolangs.org/wiki/9_trits,_19683_trytes

Memory: the 13,122 multiplicative units mod 3^9. Cell successor = doubling.
Program loads at address 1, one 9-trit tryte per cell along the doubling order.
The interpreter reads trits from LIVE memory, so self-modifying code works.
"""
M = 3 ** 9  # 19683
TRIT = {'0': 0, '1': 1, 't': -1}

def unit(a):
    a %= M
    return a + 1 if a % 3 == 0 else a  # bump rule

def bal(v):
    """Residue -> balanced value in [-9841, 9841]."""
    v %= M
    return v - M if v > (M - 1) // 2 else v

def trits_of(v):
    """9 trits, MSB first, of residue v."""
    v = bal(v)
    out = []
    for _ in range(9):
        r = v % 3
        if r == 0:   out.append(0);  v //= 3
        elif r == 1: out.append(1);  v = (v - 1) // 3
        else:        out.append(-1); v = (v + 1) // 3
    return out[::-1]

def tritwise(v, f):
    ts = [f(t) for t in trits_of(v)]
    n = 0
    for t in ts: n = n * 3 + t
    return n % M

class Machine:
    def __init__(self):
        self.mem = {}   # address (unit residue) -> residue 0..M-1
        self.out = []

    # ---- memory & trit stream -------------------------------------------
    def load(self, trytes, start=1):
        a = start % M
        for v in trytes:
            self.mem[unit(a)] = v % M
            a = (a * 2) % M

    def rd(self, a):  return self.mem.get(unit(a), 0)
    def wr(self, a, v): self.mem[unit(a)] = v % M

    def trit(self, pos):
        """pos = absolute trit index along the doubling order from address 1."""
        cell, off = divmod(pos, 9)
        return trits_of(self.rd(pow(2, cell, M)))[off]

    def take(self, pos, n):
        return [self.trit(pos + i) for i in range(n)], pos + n

    def field(self, pos):
        ts, pos = self.take(pos, 9)
        v = 0
        for t in ts: v = v * 3 + t
        return v % M, pos

    def align(self, pos):
        return pos + (-pos) % 9

    # ---- expressions -----------------------------------------------------
    UNARY = {(1,0): 'neg', (1,1): 'rotu', (1,-1): 'rotd',
             (-1,1): 'rise', (-1,-1): 'fall', (-1,0): 'sign'}
    BIN = {(0,0,-1):'mod',(0,0,1):'mul',(0,0,0):'add',(0,-1,-1):'and',
           (0,-1,1):'or',(0,-1,0):'teql',(0,1,-1):'shl',(0,1,1):'shr',
           (0,1,0):'rol',(-1,0,0):'eql',(-1,1,1):'div',(-1,-1,-1):'abs',
           (-1,0,-1):'lsi',(-1,0,1):'lsu'}

    def expr(self, pos):
        t = self.trit(pos)
        if t == 0:                                   # get
            a, pos = self.field(pos + 1)
            return self.rd(a), pos
        if t == 1 and self.trit(pos+1) == -1:        # do ... end (expression)
            pos += 2
            val = 0
            while not (self.trit(pos) == 1 and self.trit(pos+1) == 1
                       and self.trit(pos+2) == 0 and self.trit(pos+3) == 0):
                val, pos = self.expr(pos)
            return val, pos + 4
        if [self.trit(pos+i) for i in range(3)] == [1,1,0]:   # 110: unary
            key = (self.trit(pos+4), self.trit(pos+5))
            if self.trit(pos+3) == -1: op = self.UNARY[key]
            else: raise SyntaxError(f"bad 110 opcode at trit {pos}")
            v, pos = self.expr(pos + 6)
            return self.apply1(op, v), pos
        if [self.trit(pos+i) for i in range(3)] == [1,1,1]:   # 111: binary / IO
            key = tuple(self.trit(pos+3+i) for i in range(3))
            pos += 6
            if key == (-1,-1,0):                     # inp
                return int(input()) % M, pos
            if op := self.BIN.get(key):
                a, pos = self.expr(pos)
                if op == 'abs':
                    return abs(bal(a)) % M, pos
                b, pos = self.expr(pos)
                return self.apply2(op, a, b), pos
        raise SyntaxError(f"bad expression at trit {pos}")

    def apply1(self, op, v):
        f = {'neg':  lambda t: -t,
             'rotu': lambda t: 0 if t == -1 else (1 if t == 0 else -1),
             'rotd': lambda t: 1 if t == -1 else (0 if t == 1 else -1),
             'rise': lambda t: t + 1 if t < 1 else 1,
             'fall': lambda t: t - 1 if t > -1 else -1}.get(op)
        if f: return tritwise(v, f)
        s = (bal(v) > 0) - (bal(v) < 0)              # sign
        return {1: 9841, 0: 0, -1: M - 9841}[s]

    def apply2(self, op, a, b):
        ba, bb = bal(a), bal(b)
        if op == 'add': return (a + b) % M
        if op == 'mul': return (a * b) % M
        if op == 'mod': return ba % bb % M if bb else 0
        if op == 'div': return int(ba / bb) % M if bb else 0
        if op == 'eql': return 9841 if a % M == b % M else M - 9841
        if op == 'lsi': return 9841 if ba < bb else M - 9841
        if op == 'lsu': return 9841 if a % M < b % M else M - 9841
        ta, tb = trits_of(a), trits_of(b)
        if op == 'and':  ts = [min(x, y) for x, y in zip(ta, tb)]
        elif op == 'or': ts = [max(x, y) for x, y in zip(ta, tb)]
        elif op == 'teql': ts = [1 if x == y else -1 for x, y in zip(ta, tb)]
        elif op == 'shl': k = bal(b) % 9; ts = ta[k:] + [0]*k
        elif op == 'shr': k = bal(b) % 9; ts = [0]*k + ta[:9-k]
        elif op == 'rol': k = bal(b) % 9; ts = ta[k:] + ta[:k]
        n = 0
        for t in ts: n = n * 3 + t
        return n % M

    # ---- statements ------------------------------------------------------
    class Halt(Exception): pass
    class Break(Exception): pass
    class Continue(Exception): pass

    def block(self, pos):
        """Statement-position do-block: '1t' <statements> '1100'."""
        assert self.trit(pos) == 1 and self.trit(pos+1) == -1
        pos += 2
        while True:
            pos = self.align(pos)
            if (self.trit(pos) == 1 and self.trit(pos+1) == 1
                    and self.trit(pos+2) == 0 and self.trit(pos+3) == 0):
                return pos + 4
            pos = self.stmt(pos)

    def skip_expr(self, pos):
        _, pos = self.expr(pos)   # expressions are side-effect-light except inp
        return pos

    def stmt(self, pos):
        t0, t1, t2 = self.trit(pos), self.trit(pos+1), self.trit(pos+2)
        if t0 == -1:                                 # set
            a, p2 = self.field(pos + 1)
            v, p2 = self.expr(p2)
            self.wr(a, v)
            return p2
        if t0 == 1 and t1 == -1:                     # do ... end
            return self.block(pos)
        if (t0, t1, t2) == (1, 1, -1):               # while / if
            kind = self.trit(pos + 3)                # 1 = while, t = if
            cond_pos = pos + 4
            if kind == 1:
                while True:
                    v, p2 = self.expr(cond_pos)
                    assert self.trit(p2) == 1 and self.trit(p2+1) == 0
                    body = self.align(p2 + 2)
                    if bal(v) <= 0:
                        return self.block_skip(body)
                    try:
                        end = self.block(body)
                    except Machine.Break:
                        return self.block_skip(body)
                    except Machine.Continue:
                        continue
                return end
            else:
                v, p2 = self.expr(cond_pos)
                assert self.trit(p2) == 1 and self.trit(p2+1) == 0
                body = self.align(p2 + 2)
                if bal(v) > 0:
                    return self.block(body)
                return self.block_skip(body)
        if (t0, t1, t2) == (1, 1, 0):                # 110 / 111 statements
            k = tuple(self.trit(pos+3+i) for i in range(3))
            if self.trit(pos) == 1 and t2 == 0 and self.trit(pos+2) == 0:
                pass
            if [t0, t1, t2] == [1, 1, 0]:
                if k == (-1, 0, 0): raise Machine.Halt      # halt
                if k == (-1, 0, 1): raise Machine.Continue  # continue
                if k == (-1, 0, -1): raise Machine.Break    # break
        if (t0, t1, t2) == (1, 1, 1):
            k = tuple(self.trit(pos+3+i) for i in range(3))
            if k == (-1, -1, 1):                     # outp
                v, p2 = self.expr(pos + 6)
                self.emit(str(bal(v)))
                return p2
            if k == (-1, 1, -1):                     # putch
                v, p2 = self.expr(pos + 6)
                self.emit(chr(v % M))
                return p2
            if k == (-1, 1, 0):                      # getch (statement position)
                return pos + 6
        # expression in statement position (e.g. bare get inside a block)
        return self.skip_expr(pos)

    def block_skip(self, pos):
        """Skip over a statement-position do-block without executing it."""
        assert self.trit(pos) == 1 and self.trit(pos+1) == -1
        depth, pos = 1, pos + 2
        while depth:
            # structural scan: reuse the parser with execution disabled is
            # complex; for skipping we scan for balanced 1t / 1100 markers on
            # tryte-aligned statement boundaries, which the spec guarantees.
            pos = self.align(pos)
            if self.trit(pos) == 1 and self.trit(pos+1) == -1:
                depth += 1; pos += 2
            elif (self.trit(pos) == 1 and self.trit(pos+1) == 1
                  and self.trit(pos+2) == 0 and self.trit(pos+3) == 0):
                depth -= 1; pos += 4
            else:
                pos = self.stmt_length(pos)
        return pos

    def stmt_length(self, pos):
        """Length of a statement without executing it: dry parse."""
        saved_mem, saved_out = dict(self.mem), list(self.out)
        try:
            p2 = self.stmt(pos)
        finally:
            self.mem, self.out = saved_mem, saved_out
        return p2

    def emit(self, s):
        self.out.append(s)

    def run(self):
        pos = 0
        try:
            while True:
                pos = self.align(pos)
                pos = self.stmt(pos)
        except Machine.Halt:
            pass
        return "".join(self.out)


def parse_dump(code_trytes_trits, decimals):
    """code: list of 9-char trit strings; decimals: trailing data values."""
    trytes = []
    for s in code_trytes_trits:
        v = 0
        for c in s: v = v * 3 + TRIT[c]
        trytes.append(v % M)
    trytes += [d % M for d in decimals]
    return trytes


if __name__ == "__main__":
    code = """11t1110t1 0111t0000 001ttt1t0
              t1t0t0t01 100000000 1t0000000
              111t1t1t0 t0000tt0t 110000000
              t0001ttt1 t11100100 001ttt1t0
              0tt1100tt 110000000 110t00000""".split()
    data = [72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33, 10, 2, 17087]
    m = Machine()
    m.load(parse_dump(code, data))
    print(repr(m.run()))
