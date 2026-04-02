# Affine Cipher with Keyboard Ripple Hash

A custom affine cipher implementation with two twists: a **keyboard-order character set** (instead of standard ASCII order) and a **QWERTY ripple interference hash** for passphrase-based key derivation.

---

## Project Structure

```
affine.py          — Affine cipher (encrypt / decrypt + key derivation)
hash.py            — Keyboard ripple interference hash
test_roundtrip.py  — Automated test suite (10 test groups)
```

---

## Theory

### 1. The Character Set

Standard affine ciphers use ASCII order (space = 0, `!` = 1, …). This implementation reorders all 95 printable characters to follow the **physical QWERTY keyboard layout**:

| Slot | Characters |
|------|-----------|
| Row 0 | `` ` 1 2 3 4 5 6 7 8 9 0 - = q w e r t y u i o p [ `` |
| Row 1 | `] \ a s d f g h j k l ; ' z x c v b n m , . / ~` |
| Row 2 | `! @ # $ % ^ & * ( ) _ + Q W E R T Y U I O P { }` |
| Row 3 | `\| A S D F G H J K L : " Z X C V B N M < > ?` |
| Row 4 | `(space)` — placed last, the biggest key gets the final slot |

This means the numeric index `x` of each character depends on its keyboard position rather than its ASCII code point, giving the cipher a non-standard substitution baseline even before the affine transformation is applied.

### 2. The Affine Cipher

An affine cipher maps each character index `x` to a ciphertext index `y` using a linear function modulo the alphabet size `M = 95`:

```
Encrypt:  y  = (a · x + b)  mod 95
Decrypt:  x  = a⁻¹ · (y − b)  mod 95
```

- **`a`** (multiplicative key) must be **coprime with 95** (i.e., `gcd(a, 95) = 1`). Since `95 = 5 × 19`, any `a` not divisible by 5 or 19 is valid.
- **`b`** (additive key / shift) can be any integer in `[0, 95)`.
- **`a⁻¹`** is the modular inverse of `a`, computed via the Extended Euclidean Algorithm.
- Characters outside the 95-character set (e.g. newlines) are passed through unchanged.

### 3. Key Derivation — Keyboard Ripple Hash

Keys `(a, b)` are derived from a passphrase using a custom hash that models **ripple interference on the QWERTY keyboard grid**:

**How the ripple hash works:**

1. Every character in the passphrase is mapped to its physical `(col, row)` position on a QWERTY grid (with staggered row offsets matching a real keyboard).
2. Each character "drops a ripple" that spreads outward to all neighbouring keys within a range of **7 key-widths** (`RIPPLE_RANGE = 7.0`). The ripple amplitude decays linearly with distance.
3. Every key within range has its **collision counter** incremented.
4. The contribution of each neighbouring key `k` hit by ripple `i` is:

   ```
   contrib = idx(k) × amplitude × collision_count(k)
   ```

5. Each ripple is weighted by a **wave power** `37^(n−1−i) mod (10⁹+7)` so that earlier characters in the passphrase carry more weight.
6. All contributions are summed modulo `10⁹ + 7` (a large prime) to produce a single integer `h`.

**Key insight:** Keys that are physically close together on the keyboard (like `q` and `w`) produce massive collision overlap at shared neighbours and therefore very different hashes from distant key pairs (like `q` and `p`) — even for same-length strings.

**From hash to cipher keys:**

```
h   = ripple_hash(passphrase)
a   = next_coprime( (h mod 9973) mod 95 )   # low portion, via prime 9973
b   = (h // 9973) mod 95                    # upper portion, decorrelated
```

The split prime `9973` (largest prime below 10,000) ensures `a` and `b` are derived from different parts of `h` and are statistically independent.

---

## Requirements

- Python 3.10 or higher (uses `tuple[int, int]` type hint syntax)
- No third-party libraries — only the Python standard library (`math`, `sys`)

---

## Running the Code

### Encrypt / Decrypt

```python
from affine import encrypt, decrypt

ciphertext = encrypt("Hello, World!", "my_passphrase")
plaintext  = decrypt(ciphertext,      "my_passphrase")

print(ciphertext)   # encrypted string
print(plaintext)    # → "Hello, World!"
```

### Inspect key derivation

```python
from affine import derive_key, mod_inverse, M

a, b = derive_key("keyboard")
print(f"a={a}, b={b}, a⁻¹={mod_inverse(a, M)}")
```

### Run the cipher self-test

```bash
python affine.py
```

Sample output:
```
=== affine.py self-test ===

Passphrase : 'keyboard'
  a=41, b=23, a⁻¹=...
  Plaintext : 'Hello, World!'
  Encrypted : '...'
  Decrypted : 'Hello, World!'  ✓
```

### Run the hash self-test

```bash
python hash.py
```

This prints hash values for several sample strings, an avalanche check (small input change → large hash change), and a collision heatmap for the top-5 most-hit keys when hashing `"Hello"`.

### Run the full test suite

```bash
python test_roundtrip.py
```

All 10 test groups run automatically. Expected output ends with:

```
============================================================
  Results: N/N passed  |  0 failed
============================================================
```

Exit code is `0` on full pass, `1` if any test fails.

---

## Test Suite Overview

| # | Test | What it checks |
|---|------|---------------|
| 1 | Round-trip | `encrypt → decrypt` restores original for many messages × passphrases |
| 2 | Encryption changes text | Ciphertext differs from plaintext |
| 3 | Key sensitivity | Different passphrases → different ciphertexts |
| 4 | Hash determinism | Same input always produces the same hash |
| 5 | Hash avalanche | One-character change → different hash |
| 6 | Key derivation sanity | `a` is always coprime with 95 for all printable passphrases |
| 7 | Modular inverse | `a × a⁻¹ ≡ 1 (mod 95)` for all valid `a` |
| 8 | Known-vector | Deterministic encryption + coprime check for passphrase `"z"` |
| 9 | Full pipeline | `encrypt → ripple_hash(ciphertext) → decrypt` end-to-end |
| 10 | Passphrase avalanche | One-char passphrase change → different `(a, b)` keys |

---

## Design Notes

- **Why keyboard order?** It breaks the standard ASCII-order assumption that frequency-analysis attacks often rely on, without requiring a separate shuffled alphabet to be stored or communicated.
- **Why a ripple hash?** Standard hashes (MD5, SHA) treat all characters uniformly. The ripple hash is passphrase-sensitive in a spatially meaningful way — the physical layout of keys typed affects the output, making it thematically consistent with the keyboard-order cipher.
- **Why 9973 as the split prime?** Using the largest prime below 10,000 as a divider before taking `mod 95` utilises the full numeric range of `h` and minimises correlation between `a` and `b`.
- **Characters outside the set** (e.g. `\n`, Unicode) are passed through unchanged by both `encrypt` and `decrypt`, so the cipher is safe to use on arbitrary text.
