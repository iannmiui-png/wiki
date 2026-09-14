import sys, time

# fib(11) = 89, hence "89 lang".
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

_f = fib(11)
S = [_f * (_f + i) for i in range(12)]                 # [7921, 8010, ..., 8900]
GROUPS = [str(x)[-2:] for x in S]                       # last two digits of each
# GROUPS = ['21','10','99','88','77','66','55','44','33','22','11','00']
# '99' (tick 2) and '88' (tick 3) can never appear in an octal string --
# those two ticks are permanently silent. The other ten can fire.

def bf(code):
    stack = []
    matches = {}
    tape = [0] * 1000000
    for i, ch in enumerate(code):
        if ch == '7':
            stack.append(i)
        if ch == '0':
            m = stack.pop()
            matches[m] = i
            matches[i] = m
    cp = 0
    p = 0
    while cp < len(code):
        c = code[cp]
        if c == '3':
            tape[p] = (tape[p] + 1) % 256
        if c == '4':
            tape[p] = (tape[p] - 1) % 256
        if c == '6':
            ch = sys.stdin.read(1)
            tape[p] = (ord(ch) if ch else 0) % 256
        if c == '5':
            print(chr(tape[p]), end='')
        if c == '2':
            p -= 1
        if c == '1':
            p += 1
        if c == '7':
            if not tape[p]:
                cp = matches[cp]
        if c == '0':
            if tape[p]:
                cp = matches[cp]
        cp += 1

def get_clock_start(path="clock_start"):
    try:
        with open(path) as f:
            return float(f.read())
    except FileNotFoundError:
        start = time.time()
        with open(path, "x") as f:
            f.write(repr(start))
        return start

def run_once(start):
    ms = int((time.time() - start) * 1000)
    code = oct(ms)[2:]

    tick = (ms // 1000) % 12
    group = GROUPS[tick]

    print(f"[tick {tick}]", end=' ')

    removed = None
    if group in code:
        code = code.replace(group, "", 1)
        removed = group

    if removed:  # only output nonempty strings
        print(removed, end=' ')

    try:
        bf(code)
    except Exception as e:
        print(f"crashed: {e!r}", end='')
    print()  # newline to close out this tick's line

def run():
    start = get_clock_start()
    next_tick = time.time()
    while True:
        run_once(start)
        next_tick += 1
        sleep_for = next_tick - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)

if __name__ == "__main__":
    run()
