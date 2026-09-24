"""trimaxion.py - a Tri-maxion interpreter (self-contained, no jesus.py needed).

Usage:
    python3 trimaxion.py program.png
        decode a pff (positive feedback) image and run the Kontakion
        hidden inside it, printing the recovered text

    python3 trimaxion.py '"Some text!"'
        build a fresh Kontakion for the given string and derive its pff
        image from it (written to <slug>.tmax.png)

    python3 trimaxion.py program.jesus
        derive a pff image from an existing Kontakion (an Alexandrion
        registry file, the format jesus.py reads/writes)

Positive feedback (pff) format
-------------------------------
There is no carrier and no hidden low-bit trickery: a pff image's pixel
values ARE the Kontakion registry's raw bytes, laid out row-major. The
raster is built as

    "\\n" + "\\n".join(registry_lines) + ("\\0" * padding)

reshaped into a WxH grid, where W = (longest line's length) + 1 and
H = (number of lines) + 1 -- so the picture's own shape is derived
straight from the program, not chosen to fit some external carrier.
The leading newline and the null padding are both harmless: a Kontakion
line never legitimately contains either byte, so decoding just walks
the flattened raster from index 1 and stops at the first 0x00.

Every channel of a pixel carries the same value (R=G=B), so this
round-trips through a plain grayscale save (PGM, or any tool's
RGB->grayscale conversion) as well as it does through RGBA PNG/BMP --
a weighted average of three equal numbers is that number exactly.
"""
import re
import sys

from PIL import Image

M = 3 ** 9  # 19683
HEPT = "0ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# --------------------------------------------------------------------------
# terscii: jesus.py's 2-digit-per-character encoding, used only to build
# the address/word fields *inside* each Kontakion line -- unrelated to
# how a pff image stores the line's own characters (see below).
# --------------------------------------------------------------------------

_ROMAN = [
    ["ES", "SP", "0", "9", "I", "R", "_", "i", "r"],
    ["EL", "-", "1", "A", "J", "S", "a", "j", "s"],
    ["ET", "'", "2", "B", "K", "T", "b", "k", "t"],
    ["LR", ",", "3", "C", "L", "U", "c", "l", "u"],
    ["OP", ";", "4", "D", "M", "V", "d", "m", "v"],
    ["RL", ":", "5", "E", "N", "W", "e", "n", "w"],
    ["SU", ".", "6", "F", "O", "X", "f", "o", "x"],
    ["HT", "!", "7", "G", "P", "Y", "g", "p", "y"],
    ["SD", "?", "8", "H", "Q", "Z", "h", "q", "z"],
]
_C2T, _T2C = {}, {}
for _r, _row in enumerate(_ROMAN):
    for _c, _ch in enumerate(_row):
        code = f"{_r}{_c}"
        if _ch == "SP":
            _C2T[" "] = code
            _T2C[code] = " "
        elif len(_ch) == 1:
            _C2T[_ch] = code
            _T2C[code] = _ch


def terscii(s):
    return "".join(_C2T.get(ch, "00") for ch in s)


def unterscii(t):
    return "".join(_T2C.get(t[i:i + 2], "\0") for i in range(0, len(t), 2))


def hept_to_int(h):
    v = 0
    for ch in h:
        v = v * 27 + HEPT.index(ch)
    return v


def to_hept(n):
    n %= M
    if n == 0:
        return "0"
    d = []
    while n:
        n, r = divmod(n, 27)
        d.append(HEPT[r])
    return "".join(reversed(d))


def dlog2(v):
    n, k = 1, 0
    while n != v % M:
        n, k = n * 2 % M, k + 1
    return k


def _bal9(v):
    v %= M
    if v > (M - 1) // 2:
        v -= M
    out = []
    for _ in range(9):
        r = v % 3
        if r == 0:
            out.append('0'); v //= 3
        elif r == 1:
            out.append('1'); v = (v - 1) // 3
        else:
            out.append('t'); v = (v + 1) // 3
    return "".join(reversed(out))


def assemble(text):
    """Trytes of: while p != endptr do putch [p] ; p *= 2 end halt, data."""
    addr = lambda t: pow(2, t, M)
    data = [ord(c) % M for c in text]
    T_P, T_DATA = 7, 15
    T_CONST2 = T_DATA + len(data)
    T_ENDPTR = T_CONST2 + 1

    s = ""

    def pad():
        nonlocal s
        while len(s) % 9:
            s += '0'

    s += ("11t1" + "110t10" + "111t00"
          + "0" + _bal9(addr(T_P)) + "0" + _bal9(addr(T_ENDPTR)) + "10")
    pad()
    s += "1t"; pad()
    s += "111t1t" + "1t" + "0" + _bal9(addr(T_DATA)) + "1100"; pad()
    s += ("t" + _bal9(addr(T_P)) + "111001"
          + "0" + _bal9(addr(T_P)) + "0" + _bal9(addr(T_CONST2)))
    pad()
    s += "1100"; pad()
    s += "110t00"; pad()

    trytes = []
    for i in range(0, len(s), 9):
        v = 0
        for c in s[i:i + 9]:
            v = v * 3 + {'0': 0, '1': 1, 't': -1}[c]
        trytes.append(v % M)
    return trytes + data + [2, addr(T_CONST2)]


def generate_kontakion(text):
    trytes = assemble(text)
    word = terscii(text)
    rows = []
    for k, v in enumerate(trytes):
        radix = 29996 - k
        a = f"{format(radix & 0xFFFFFF, '06X')}{format(k, '03X')}"
        rows.append((to_hept(v), a, k))
    rows.sort(key=lambda x: (hept_to_int(x[0]), x[2]))
    return [f"{i}:{h}<{terscii(a)}>{word}" for i, (h, a, k) in enumerate(rows)]


def read_jesus(path):
    with open(path) as f:
        return [ln.strip() for ln in f if ":" in ln and "<" in ln]


def load_kontakion(lines):
    cells = {}
    for line in lines:
        hept = line.split(":", 1)[1].split("<", 1)[0]
        t9 = line.split("<", 1)[1].split(">", 1)[0]
        k = int(unterscii(t9)[-3:], 16)
        cells[k] = hept_to_int(hept)
    return cells


def run_kontakion(lines):
    """Extract the text a decoded Kontakion registry encodes. Bounded by
    construction (the pointer doubles mod the odd number M, so it can
    only cycle through at most M states) -- Tri-maxion is meant to be
    total, so this raises instead of ever looping forever."""
    cells = load_kontakion(lines)
    k_start = dlog2(cells[7])
    k_end = dlog2(cells[max(cells)])
    if k_end < k_start or k_end - k_start > M:
        raise ValueError("pointer program never reaches its stated end -- "
                          "malformed pff image")
    return "".join(chr(cells[k]) for k in range(k_start, k_end))


# --------------------------------------------------------------------------
# pff (positive feedback): the image's shape IS the registry's shape, and
# every pixel's value IS one raw byte of the registry text -- no hidden
# indirection. See module docstring for the exact byte layout.
# --------------------------------------------------------------------------

def encode_pff(lines):
    """Build a pff image straight from a Kontakion registry. Returns a
    PIL Image; nothing outside the registry itself is consulted.

    Width/height are derived from these exact lines (longest line + 1,
    line count + 1), so the canvas always has room for its own content
    by construction -- there's no separate carrier to run out of space,
    and no "image too small" failure mode to guard against."""
    width = max((len(ln) for ln in lines), default=0) + 1
    height = len(lines) + 1
    total = width * height

    content = "\n" + "\n".join(lines)
    assert len(content) <= total  # guaranteed by the width/height formula above
    raster = [ord(c) for c in content] + [0] * (total - len(content))

    im = Image.new("RGBA", (width, height))
    px = im.load()
    for i, v in enumerate(raster):
        x, y = i % width, i // width
        px[x, y] = (v, v, v, 255)
    return im


def decode_pff(path):
    """Read a pff image back into Kontakion registry lines."""
    im = Image.open(path)
    if im.mode not in ("L", "RGB", "RGBA"):
        im = im.convert("RGB")
    width, height = im.size
    px = im.load()

    def value_at(i):
        p = px[i % width, i // width]
        return p if isinstance(p, int) else p[0]

    chars = []
    for i in range(1, width * height):  # index 0 is the required leading "\n"
        v = value_at(i)
        if v == 0:
            break                        # null padding: end of real data
        chars.append(chr(v))
    return "".join(chars).split("\n")


# --------------------------------------------------------------------------

def slug(text):
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return (s[:24] or "kontakion")


def main():
    if len(sys.argv) != 2:
        print("usage:")
        print("  python3 trimaxion.py program.png     decode+run a pff image")
        print("  python3 trimaxion.py '\"text\"'        derive a pff image for text")
        print("  python3 trimaxion.py program.jesus   derive a pff image from a Kontakion")
        print("  python3 trimaxion.py -               'cat': encode stdin as a pff image")
        print("  python3 trimaxion.py program.txt     encode a text file's exact contents")
        print("                                        (any of these last three bake the")
        print("                                        text in at generation time -- a")
        print("                                        Kontakion's output is fixed once")
        print("                                        made, so this is what it will")
        print("                                        always echo back)")
        return

    arg = sys.argv[1]
    IMAGE_EXTS = (".png", ".bmp", ".pgm", ".ppm", ".gif", ".tif", ".tiff")

    if arg == "-":
        text = sys.stdin.read()
        lines = generate_kontakion(text)
        out = "cat.tmax.png"
        im = encode_pff(lines)
        im.save(out)
        print(f"Generated a cat of stdin ({len(text)} chars) -> {out} "
              f"({im.size[0]}x{im.size[1]})")
        return

    if '"' in arg or "'" in arg:
        text = arg.strip().strip('"\'')
        lines = generate_kontakion(text)
        out = slug(text) + ".tmax.png"
        im = encode_pff(lines)
        im.save(out)
        print(f"Generated Kontakion for {text!r} -> {out} ({im.size[0]}x{im.size[1]})")
        return

    if arg.endswith(".jesus"):
        lines = read_jesus(arg)
        out = arg.rsplit(".", 1)[0] + ".tmax.png"
        im = encode_pff(lines)
        im.save(out)
        print(f"Derived pff image from {arg} -> {out} ({im.size[0]}x{im.size[1]})")
        return

    if arg.lower().endswith(IMAGE_EXTS):
        lines = decode_pff(arg)
        text = run_kontakion(lines)
        print("Text from pff Kontakion:", repr(text))
        return

    # anything else: a plain text file, taken verbatim (newlines and all)
    with open(arg, "r", newline="") as f:
        text = f.read()
    lines = generate_kontakion(text)
    out = arg.rsplit(".", 1)[0] + ".tmax.png" if "." in arg else arg + ".tmax.png"
    im = encode_pff(lines)
    im.save(out)
    print(f"Generated Kontakion from {arg} ({len(text)} chars) -> {out} "
          f"({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
