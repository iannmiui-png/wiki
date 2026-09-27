import sys

K = int(
 "94522385906913185446771685760332001833521738630840852762753182115223546287"
 "63231360594706925388931138237215903222640767476400096069360530679935418459"
 "80836848161004676371974799422742591398733768476573703679111089239134980278"
 "94518328191154876563202695767790736646006073182273183936539961551307911343"
 "02835878212423809302964077062823416265983444183318323940373872544663585781"
 "87158879914091334845531264160250774167081287613157254659555348368699325828"
 "99469631003369580373519631776199198327125268117203795119121108798901674842"
 "62879803610293602475520")

W, H = 106, 17

def read_pbm(data: bytes):
    if data[:2] == b'P1':
        toks = data[2:].split()
        w, h = int(toks[0]), int(toks[1])
        bits = ''.join(t.decode() for t in toks[2:])
        px = [int(c) for c in bits if c in '01']
        if len(px) < w*h:
            raise ValueError(f"P1 data too short: {len(px)} < {w*h}")
        return [px[r*w:(r+1)*w] for r in range(h)]
    raise ValueError("not a P1 PBM")

def tupper_k(rows):
    h = len(rows); w = len(rows[0])
    if h != H:
        raise ValueError(f"bitmap must be {H} rows tall, got {h}")
    if w > W:
        raise ValueError(f"bitmap wider than {W} columns ({w})")
    n = 0
    for r in range(h):
        for c in range(w):
            if rows[r][c]:
                x, y = (W - 1) - c, (H - 1) - r
                n |= 1 << (17*x + y)
    return 17 * n

def main(argv):
    data = open(argv[1], 'rb').read() if len(argv) > 1 else sys.stdin.buffer.read()
    k = tupper_k(read_pbm(data))
    if k == K:
        print(4)
    else:
        intervals = abs(k - K) // 17
        print(chr(intervals % 128))

if __name__ == '__main__':
    main(sys.argv)
