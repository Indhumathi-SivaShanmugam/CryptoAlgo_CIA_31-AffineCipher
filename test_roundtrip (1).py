"""
test_roundtrip.py — Automated Round-Trip Test Suite
====================================================
Tests:
  1. encrypt → decrypt round-trip (many messages × many keys)
  2. Hash determinism (same input → same hash every time)
  3. Hash sensitivity (one-char change → different hash)
  4. Key derivation sanity (a is always coprime with 95)
  5. Edge cases (empty string passthrough, single char, full charset)
  6. Known-vector test (round-trip only — expected value depends on ripple_hash)
  7. Mod inverse correctness
  8. Full pipeline (encrypt → hash → decrypt)

Run:  python test_roundtrip.py
All tests print PASS / FAIL; exits with code 0 only if all pass.
"""

import sys
import math
from affine import encrypt, decrypt, derive_key, mod_inverse, CHARSET, M
from hash import ripple_hash, hash_hex


_PASS = 0
_FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓  {name}")
    else:
        _FAIL += 1
        msg = f"  ✗  FAIL: {name}"
        if detail:
            msg += f"\n         {detail}"
        print(msg)


# ── Test 1: Round-trip across many messages and passphrases ──────────────────
def test_roundtrip():
    print("\n[1] Round-trip: encrypt → decrypt")

    messages = [
        "Hello, World!",
        "The quick brown fox jumps over the lazy dog.",
        "1234567890",
        "!@#$%^&*()",
        "aAbBcCdDeE",
        "   spaces   ",
        "`~-_=+[{]}|;:',<.>/?",
        CHARSET,                   # encrypt the full charset itself
    ]

    passphrases = [
        "keyboard",
        "my_secret_2024",
        "z",
        "AAAA",
        "!@#$",
        "a" * 100,   # long passphrase
    ]

    for pw in passphrases:
        for msg in messages:
            ct = encrypt(msg, pw)
            rt = decrypt(ct, pw)
            check(
                f"roundtrip pw={pw!r:20s} msg={msg[:20]!r}",
                rt == msg,
                f"Expected {msg!r}, got {rt!r}"
            )


# ── Test 2: Encryption changes the text ──────────────────────────────────────
def test_encryption_changes_text():
    print("\n[2] Encryption actually changes the text")
    msg = "Hello"
    ct = encrypt(msg, "keyboard")
    check("ciphertext differs from plaintext", ct != msg)


# ── Test 3: Different passphrases produce different ciphertexts ──────────────
def test_key_sensitivity():
    print("\n[3] Key sensitivity")
    msg = "SameMessage"
    ct1 = encrypt(msg, "key1")
    ct2 = encrypt(msg, "key2")
    check("different keys → different ciphertexts", ct1 != ct2,
          f"ct1={ct1!r}  ct2={ct2!r}")


# ── Test 4: Hash determinism ─────────────────────────────────────────────────
def test_hash_determinism():
    print("\n[4] Hash determinism")
    samples = ["Hello", "World", CHARSET, ""]
    for s in samples:
        h1 = ripple_hash(s)
        h2 = ripple_hash(s)
        check(f"deterministic hash for {s[:20]!r}", h1 == h2)


# ── Test 5: Hash sensitivity (avalanche) ─────────────────────────────────────
def test_hash_sensitivity():
    print("\n[5] Hash sensitivity (avalanche)")
    pairs = [
        ("keyboard",  "Keyboard"),    # case change
        ("abc",       "abd"),          # last char change
        ("abc",       "abcd"),         # length change
        ("Hello!",    "Hello?"),       # punctuation change
    ]
    for a, b in pairs:
        ha = ripple_hash(a)
        hb = ripple_hash(b)
        check(f"hash({a!r}) ≠ hash({b!r})", ha != hb,
              f"Both hashed to {hex(ha)}")


# ── Test 6: Key derivation — a is always coprime with 95 ─────────────────────
def test_key_derivation():
    print("\n[6] Key derivation: a is always coprime with 95")
    passphrases = [chr(c) for c in range(32, 127)]
    passphrases += ["keyboard", "my_secret_2024", "z", "!@#$", "a"*50]
    fails = [pw for pw in passphrases if math.gcd(derive_key(pw)[0], M) != 1]
    check(f"All {len(passphrases)} passphrases yield valid a",
          len(fails) == 0, f"Failed: {fails[:5]}")


# ── Test 7: mod_inverse correctness ──────────────────────────────────────────
def test_mod_inverse():
    print("\n[7] Modular inverse correctness")
    valid_as = [a for a in range(2, M) if math.gcd(a, M) == 1]
    for a in valid_as[:20]:
        a_inv = mod_inverse(a, M)
        check(f"{a} × {a_inv} ≡ 1 (mod 95)",
              (a * a_inv) % M == 1)


# ── Test 8: Known-vector (round-trip, not fixed expected value) ───────────────
def test_known_vector():
    """
    The expected ciphertext is determined by ripple_hash, so we verify the
    round-trip property rather than a hardcoded value. We do spot-check that
    derive_key produces a valid (coprime) a for the passphrase 'z'.
    """
    print("\n[8] Known-vector test")
    pw = "z"
    pt = "Hello, World!"
    a, b = derive_key(pw)
    check(f"derive_key('z') gives coprime a={a}", math.gcd(a, M) == 1)

    ct = encrypt(pt, pw)
    rt = decrypt(ct, pw)
    check(f"encrypt then decrypt 'z' passphrase restores plaintext", rt == pt,
          f"got {rt!r}")

    # Determinism: encrypting twice gives same result
    ct2 = encrypt(pt, pw)
    check("encryption is deterministic", ct == ct2)


# ── Test 9: Full pipeline (encrypt → hash → decrypt) ─────────────────────────
def test_full_pipeline():
    print("\n[9] Full pipeline: encrypt → hash → decrypt")
    cases = [
        ("Hello, World!",                 "keyboard"),
        ("Affine Cipher: my twist!",      "my_secret_2024"),
        (CHARSET,                          "all_chars"),
    ]
    for pt, pw in cases:
        ct = encrypt(pt, pw)
        h  = ripple_hash(ct)
        rt = decrypt(ct, pw)
        check(f"hash in [0, 10^9+7) for pw={pw!r}",
              0 <= h < 1_000_000_007)
        check(f"roundtrip for pw={pw!r} msg={pt[:20]!r}",
              rt == pt, f"got {rt!r}")


# ── Test 10: Ripple hash used for key derivation — avalanche on passphrase ────
def test_passphrase_avalanche():
    print("\n[10] Passphrase avalanche via ripple_hash key derivation")
    pairs = [
        ("keyboard", "Keyboard"),
        ("abc",      "abd"),
        ("hello",    "hellp"),
    ]
    for pw1, pw2 in pairs:
        a1, b1 = derive_key(pw1)
        a2, b2 = derive_key(pw2)
        different = (a1 != a2) or (b1 != b2)
        check(f"keys differ for {pw1!r} vs {pw2!r}", different,
              f"both gave a={a1}, b={b1}")


# ── Runner ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Affine Cipher — Automated Test Suite")
    print("=" * 60)

    test_roundtrip()
    test_encryption_changes_text()
    test_key_sensitivity()
    test_hash_determinism()
    test_hash_sensitivity()
    test_key_derivation()
    test_mod_inverse()
    test_known_vector()
    test_full_pipeline()
    test_passphrase_avalanche()

    print(f"\n{'='*60}")
    total = _PASS + _FAIL
    print(f"  Results: {_PASS}/{total} passed  |  {_FAIL} failed")
    print(f"{'='*60}\n")

    sys.exit(0 if _FAIL == 0 else 1)
