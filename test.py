"""
test.py — 5 input test cases
===========================================
Each test encrypts a message, decrypts it, and confirms we get back the original.
Prints a clear PASS / FAIL for each case.
"""

from affine import encrypt, decrypt, derive_key, mod_inverse, M

tests = [
    # (plaintext,                    passphrase,       description)
    ("Hello World",                  "keyboard",       "basic greeting"),
    ("The quick brown fox",          "secret",         "common pangram slice"),
    ("1234567890",                   "numbers123",     "digits only"),
    ("!@#$%^&*()",                   "symbols!",       "special characters"),
    ("Attack at dawn",               "wartime",        "classic cipher phrase"),
]

print("=" * 60)
print("  Simple 5-Input Test")
print("=" * 60)

passed = 0
for pt, pw, desc in tests:
    a, b = derive_key(pw)
    ct = encrypt(pt, pw)
    rt = decrypt(ct, pw)
    ok = rt == pt
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    print(f"\n  [{status}] {desc}")
    print(f"    passphrase : {pw!r}  →  a={a}, b={b}, a⁻¹={mod_inverse(a, M)}")
    print(f"    plaintext  : {pt!r}")
    print(f"    encrypted  : {ct!r}")
    print(f"    decrypted  : {rt!r}")

