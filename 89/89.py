import sys, time, select

def try_read_byte():
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            return ord(ch) if ch else 0
    except Exception:
        pass
    return 0

def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

_f = fib(11)
S = [_f * (_f + i) for i in range(12)]                 # [7921, 8010, ..., 8900]
GROUPS = [str(x)[-2:] for x in S]                       # last two digits of each
# GROUPS = ['21','10','99','88','77','66','55','44','33','22','11','00']

def bf(code, max_steps=200000):
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
    steps = 0
    while cp < len(code):
        steps += 1
        if steps > max_steps:
            return
        c = code[cp]
        if c == '3':
            tape[p] = (tape[p] + 1) % 256
        if c == '4':
            tape[p] = (tape[p] - 1) % 256
        if c == '6':
            tape[p] = try_read_byte() % 256
        if c == '5':
            if tape[p] == 4:
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
    label = f"[{S[tick]}]"

    print(label, end=' ')

    removed = None
    if group in code:
        code = code.replace(group, "", 1)
        removed = group

    if removed:
        print(removed, end=' ')

    try:
        bf(code)
    except Exception:
        pass
    print()

def run():
    start = get_clock_start()
    tick_ms = 89
    next_tick = time.time()
    while True:
        run_once(start)
        next_tick += tick_ms / 729
        sleep_for = next_tick - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)

if __name__ == "__main__":
    run()
