"""
hash.py  —  Keyboard Ripple Interference Hash
==============================================
Each typed character drops a ripple on the physical QWERTY keyboard grid.
The ripple spreads outward, hitting neighbouring keys. Every key tracks
how many ripples have landed on it (collision count). That count, combined
with the key's distance from the source and its charset index, feeds the hash.

Algorithm
---------
For each character c_i at keyboard position p_i:

  1. For every other key k on the board:
       dist      = Euclidean distance(p_i, k)  in key-units
       amplitude = max(0,  1 - dist / RIPPLE_RANGE)   # decays with distance
       collisions[k] += 1                              # count ripple arrivals

  2. Contribution of key k when hit by ripple i:
       contrib = idx(k) * amplitude * collisions[k]

  3. Wave power (characters earlier in string ripple further, hit more):
       power = 37^(n-1-i)  mod  MODULUS

  4. Hash accumulates:
       H += contrib * power   (mod MODULUS)

Result: keys physically close to many typed characters accumulate high
collision counts and dominate the hash. Typing 'qw' (neighbours) produces
massive collision overlap at shared neighbours; 'qp' (far apart) barely
overlaps — completely different hash even for same-length strings.

Parameters
----------
RIPPLE_RANGE = 7.0   keys  (ripple dies out after 7 key-widths)
BASE         = 37          (polynomial wave power base)
MODULUS      = 10^9 + 7   (large prime)
"""

import math

# ── Keyboard grid ─────────────────────────────────────────────────────────────
# Each row: (chars, col_offset)  — offset shifts keys right (like a real board)
_ROWS = [
    ("`1234567890-=",   0.0),
    ("qwertyuiop[]\\", 0.5),
    ("asdfghjkl;'",    0.8),
    ("zxcvbnm,./",     1.3),
]
_SHIFT_ROWS = [
    ("~!@#$%^&*()_+",  0.0),
    ("QWERTYUIOP{}|",  0.5),
    ('ASDFGHJKL:"',    0.8),
    ("ZXCVBNM<>?",     1.3),
]

# charset (same order as affine.py)
from affine import CHARSET, _CHAR_TO_IDX

def _char_idx(ch: str) -> int:
    return _CHAR_TO_IDX.get(ch, ord(ch) % 95)

# Build key position map: ch -> (col_pos, row_pos)
_KEY_POS: dict[str, tuple[float, float]] = {}

for _ri, ((_chars, _ox), (_schars, _sox)) in enumerate(zip(_ROWS, _SHIFT_ROWS)):
    for _ci, _ch in enumerate(_chars):
        _KEY_POS[_ch] = (_ci + _ox, _ri)
    for _ci, _ch in enumerate(_schars):
        _KEY_POS[_ch] = (_ci + _sox, _ri + 0.5)   # shift row sits half-step below

_KEY_POS[' '] = (5.0, 4.5)  # space bar — bottom center

ALL_KEYS = list(_KEY_POS.keys())

# ── Core ──────────────────────────────────────────────────────────────────────
RIPPLE_RANGE = 7.0
BASE         = 37
MODULUS      = 1_000_000_007


def _key_dist(a: str, b: str) -> float:
    """Euclidean distance between two keys in key-unit coordinates."""
    ax, ay = _KEY_POS.get(a, (0, 0))
    bx, by = _KEY_POS.get(b, (0, 0))
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def _amplitude(dist: float) -> float:
    """Ripple strength at a given distance — linear decay to zero at RIPPLE_RANGE."""
    return max(0.0, 1.0 - dist / RIPPLE_RANGE)


def ripple_hash(text: str) -> int:
    """
    Keyboard ripple interference hash.

    Steps:
      1. Each character sends a ripple across the keyboard grid.
      2. Every key within RIPPLE_RANGE gets hit; its collision counter increments.
      3. Contribution = idx(neighbour) * amplitude * collision_count.
      4. Scaled by wave power 37^(n-1-i) and accumulated mod 10^9+7.

    Returns int in [0, MODULUS).
    """
    if not text:
        return 0

    n = len(text)
    collision_count: dict[str, int] = {k: 0 for k in ALL_KEYS}
    H = 0

    for i, ch in enumerate(text):
        if ch not in _KEY_POS:
            # Out-of-layout character: treat as raw charset index contribution
            H = (H + _char_idx(ch) * pow(BASE, n - 1 - i, MODULUS)) % MODULUS
            continue

        power = pow(BASE, n - 1 - i, MODULUS)

        for neighbour in ALL_KEYS:
            dist = _key_dist(ch, neighbour)
            amp  = _amplitude(dist)
            if amp <= 0:
                continue

            collision_count[neighbour] += 1
            col = collision_count[neighbour]

            contrib = int(_char_idx(neighbour) * amp * col)
            H = (H + contrib * power) % MODULUS

    return H


def hash_hex(text: str) -> str:
    """Return ripple_hash as zero-padded hex, e.g. '0x1A2B3C4D'."""
    return f"0x{ripple_hash(text):08X}"


def collision_report(text: str) -> list[dict]:
    """
    Return per-key collision counts after hashing text.
    Useful for visualisation and README examples.
    """
    if not text:
        return []

    collision_count: dict[str, int] = {k: 0 for k in ALL_KEYS}

    for ch in text:
        if ch not in _KEY_POS:
            continue
        for neighbour in ALL_KEYS:
            if _amplitude(_key_dist(ch, neighbour)) > 0:
                collision_count[neighbour] += 1

    report = [
        {"key": k, "idx": _char_idx(k), "collisions": v,
         "pos": _KEY_POS[k]}
        for k, v in collision_count.items() if v > 0
    ]
    return sorted(report, key=lambda r: -r["collisions"])


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== keyboard ripple hash — self test ===\n")

    samples = [
        ("Hello, World!",          "mixed case + punctuation"),
        ("Hello, World?",          "1-char change -> avalanche"),
        ("qw",                     "neighbours -> heavy overlap"),
        ("qp",                     "far apart  -> sparse overlap"),
        ("keyboard",               "passphrase example"),
        ("Keyboard",               "case change"),
        ("",                       "empty string"),
    ]

    for text, note in samples:
        print(f"  {text!r:22s}  {hash_hex(text)}   # {note}")

    print()
    print("Avalanche check:")
    pairs = [("keyboard","Keyboard"), ("qw","qp"), ("abc","abd")]
    for a, b in pairs:
        ha, hb = ripple_hash(a), ripple_hash(b)
        print(f"  {a!r:12s} -> {hex(ha)}")
        print(f"  {b!r:12s} -> {hex(hb)}   delta={abs(ha-hb):,}")
        print()

    print("Top-5 collision keys for 'Hello':")
    for row in collision_report("Hello")[:5]:
        bar = "█" * row["collisions"]
        print(f"  '{row['key']}' idx={row['idx']:2d}  hits={row['collisions']}  {bar}")
