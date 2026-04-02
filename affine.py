"""
affine.py — Affine Cipher with Keyboard-Order Symbol Set
=========================================================
My Twist: Instead of standard ASCII order (space=32 … ~=126),
the symbol set follows the physical keyboard layout you see
when you look down at a QWERTY board:

    Row 0 (number row + top QWERTY): ` 1 2 3 4 5 6 7 8 9 0 - = q w e r t y u i o p [
    Row 1 (home row):                ] \\ a s d f g h j k l ; ' z x c v b n m , . / ~
    Row 2 (shift + number row):      ! @ # $ % ^ & * ( ) _ + Q W E R T Y U I O P { }
    Row 3 (shift + home row):        | A S D F G H J K L : " Z X C V B N M < > ?
    Row 4 (space bar):               (space)

Total: 95 printable characters (same set as printable ASCII, different order).
Space is placed last — it's the biggest key on the keyboard, so it gets the final slot.

Affine cipher:
    Encrypt: E(x) = (a * x + b) mod 95
    Decrypt: D(y) = a_inv * (y - b) mod 95

Key derivation from passphrase (keyboard-themed):
    h   = ripple_hash(passphrase)          — walks the QWERTY grid
    a   = next_coprime( (h % 9973) % 95 )  — low portion, folded through prime 9973
    b   = (h // 9973) % 95                 — upper portion, decorrelated from a
    next_coprime: bump a up by 1 until gcd(a, 95) == 1, min value 2

    9973 is the largest prime below 10000. Dividing through it before taking mod 95
    uses the full numeric range of ripple_hash and keeps a and b independent.
"""

import math

# ── Keyboard-order character set ──────────────────────────────────────────────
# Row 0: number row (left to right), then QWERTY top row  [24 chars]
_ROW0 = "`1234567890-=qwertyuiop["
# Row 1: ] \ then ASDF home row, then ZXCV bottom row     [24 chars]
_ROW1 = r"]\asdfghjkl;'" + "zxcvbnm,./~"
# Row 2: shift + number row, then shift + top row         [24 chars]
_ROW2 = "!@#$%^&*()_+QWERTYUIOP{}"
# Row 3: shift + home/bottom rows                         [22 chars]
_ROW3 = '|ASDFGHJKL:"ZXCVBNM<>?'
# Space bar — placed last                                  [1 char]
_SPACE = " "

CHARSET = _ROW0 + _ROW1 + _ROW2 + _ROW3 + _SPACE   # length = 95
assert len(CHARSET) == 95, f"Charset length is {len(CHARSET)}, expected 95"
assert len(set(CHARSET)) == 95, "Charset has duplicate characters!"

# Pre-build index dict for O(1) lookup
_CHAR_TO_IDX = {ch: i for i, ch in enumerate(CHARSET)}

M = 95  # modulus = size of symbol set

_SPLIT_PRIME = 9973   # largest prime below 10 000; used to decorrelate a and b


# ── Modular arithmetic helpers ────────────────────────────────────────────────

def _extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    """Return (gcd, x, y) such that a*x + b*y = gcd."""
    if b == 0:
        return a, 1, 0
    g, x, y = _extended_gcd(b, a % b)
    return g, y, x - (a // b) * y


def mod_inverse(a: int, m: int) -> int:
    """Return a^-1 mod m, or raise ValueError if it doesn't exist."""
    g, x, _ = _extended_gcd(a % m, m)
    if g != 1:
        raise ValueError(f"{a} has no inverse mod {m} (gcd={g})")
    return x % m


def next_coprime(value: int, m: int = M) -> int:
    """
    Find the smallest integer >= max(value, 2) that is coprime with m.
    95 = 5 × 19, so any a not divisible by 5 or 19 works.
    """
    a = max(value, 2)
    while math.gcd(a, m) != 1:
        a += 1
    return a


# ── Key derivation ────────────────────────────────────────────────────────────

def derive_key(passphrase: str) -> tuple[int, int]:
    """
    Derive affine key (a, b) from a passphrase using the keyboard ripple hash.

    The ripple hash walks the QWERTY grid — each passphrase character drops a
    ripple that spreads to neighbouring keys, accumulating collision counts.
    The resulting integer h is split into two decorrelated halves:

        a = next_coprime( (h % 9973) % 95 )
        b = (h // 9973) % 95

    Folding through 9973 (largest prime < 10000) before taking mod 95 uses the
    full numeric range of h and prevents a and b from correlating.

    Returns: (a, b)
    Raises: ValueError if passphrase is empty.
    """
    if not passphrase:
        raise ValueError("Passphrase cannot be empty.")

    from hash import ripple_hash          # import here to avoid circular import
    h = ripple_hash(passphrase)           # int in [0, 10^9 + 7)

    a = next_coprime((h % _SPLIT_PRIME) % M, M)
    b = (h // _SPLIT_PRIME) % M

    return a, b


# ── Core cipher ───────────────────────────────────────────────────────────────

def encrypt(plaintext: str, passphrase: str) -> str:
    """
    Encrypt plaintext using the Affine cipher with keyboard-order charset.

    Characters NOT in CHARSET are passed through unchanged (e.g. newlines).
    """
    a, b = derive_key(passphrase)
    result = []
    for ch in plaintext:
        if ch in _CHAR_TO_IDX:
            x = _CHAR_TO_IDX[ch]
            y = (a * x + b) % M
            result.append(CHARSET[y])
        else:
            result.append(ch)   # pass-through for out-of-set chars
    return "".join(result)


def decrypt(ciphertext: str, passphrase: str) -> str:
    """
    Decrypt ciphertext using the Affine cipher with keyboard-order charset.

    Characters NOT in CHARSET are passed through unchanged.
    """
    a, b = derive_key(passphrase)
    a_inv = mod_inverse(a, M)
    result = []
    for ch in ciphertext:
        if ch in _CHAR_TO_IDX:
            y = _CHAR_TO_IDX[ch]
            x = (a_inv * (y - b)) % M
            result.append(CHARSET[x])
        else:
            result.append(ch)
    return "".join(result)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== affine.py self-test ===\n")
    print(f"CHARSET ({len(CHARSET)} chars):")
    print(f"  {CHARSET}\n")

    examples = [
        ("Hello, World!", "keyboard"),
        ("Affine cipher rocks!", "my_secret_2024"),
    ]

    for pt, pw in examples:
        a, b = derive_key(pw)
        ct = encrypt(pt, pw)
        rt = decrypt(ct, pw)
        status = "✓" if rt == pt else "✗ FAIL"
        print(f"Passphrase : {pw!r}")
        print(f"  a={a}, b={b}, a⁻¹={mod_inverse(a, M)}")
        print(f"  Plaintext : {pt!r}")
        print(f"  Encrypted : {ct!r}")
        print(f"  Decrypted : {rt!r}  {status}")
        print()
