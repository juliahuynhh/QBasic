# QBasic

A small quantum programming language and circuit simulator, written from scratch in pure Python. Write a circuit in a simple text format, and QBasic parses it, simulates the quantum state, draws the circuit in ASCII, and prints a histogram of measurement results.

No dependencies. No quantum libraries. Just the Python standard library.

```
q0: -[H]---*---[M]---
           |
q1: ------(+)--[M]---

Results after 200 shots (qubit 0 is the leftmost bit):
  00 | ############################ 97 (48%)
  11 | ############################## 103 (52%)
```

## Quick start

Requires Python 3.8+.

```bash
python qbasic.py            # runs the built-in Bell state demo
python qbasic.py bell.q     # runs a program file
python qbasic.py random.q
```

## The language

One command per line. `#` starts a comment. Commands are case-insensitive.

| Command | Meaning |
|---|---|
| `qubits(N)` | Number of qubits. Must come first. |
| `shots(N)` | Number of times to run the circuit (optional, default 100). |
| `measure()` | Measure all qubits. Must come last. |
| `GATE(q)` | Apply a single-qubit gate to qubit `q` (numbering starts at 0). |
| `GATE(c, t)` | Apply a two-qubit gate (control first, then target). |

### Supported gates

| Gate | Qubits | Description |
|---|---|---|
| `H` | 1 | Hadamard (creates superposition) |
| `X` | 1 | Pauli-X (bit flip, 0 ↔ 1) |
| `Y` | 1 | Pauli-Y |
| `Z` | 1 | Pauli-Z (phase flip) |
| `S` | 1 | Phase gate (π/2) |
| `T` | 1 | T gate (π/4 phase) |
| `CNOT` | 2 | Flip target if control is 1 |
| `CZ` | 2 | Phase flip if both qubits are 1 |
| `SWAP` | 2 | Swap two qubits |

### Error messages

QBasic reports errors with line numbers, for example:

```
error: line 3: qubit 2 doesn't exist (you have qubits 0 to 1)
error: line 4: CNOT needs 2 qubit number(s), got 1
error: line 5: gates must come before measure()
```

## How it works

A program goes through four stages:

1. **Tokenize**: a regex-based lexer splits each line into words, numbers, and punctuation, and drops comments.
2. **Parse**: checks that each line has the form `NAME(number, ...)`, validates argument counts and qubit indices, and builds the program (qubit count, gate list, shots, measurement flag).
3. **Simulate**: a statevector simulator stores all `2^n` complex amplitudes and applies each gate directly to the amplitudes using bit operations (no matrix libraries).
4. **Draw**: renders the circuit as an ASCII diagram, then measures by sampling `shots` outcomes weighted by `|amplitude|²` and prints a histogram.

## Example programs

### `bell.q`: Bell state

Creates an entangled pair. Both qubits always agree: you get `00` or `11` (roughly 50/50), never `01` or `10`.

```
# Bell state: two qubits that always agree
qubits(2)
H(0)
CNOT(0, 1)
measure()
```

Output (varies run to run because measurement is random):

```
q0: -[H]---*---[M]---
           |
q1: ------(+)--[M]---

Results after 100 shots (qubit 0 is the leftmost bit):
  00 | ##################### 41 (41%)
  11 | ############################## 59 (59%)
```

### `random.q`: basic gate test

A deterministic sanity check: `X` flips qubit 1 to `1`, then `CZ` is applied. Since qubit 0 stays `0`, `CZ` has no effect on the outcome, so the result is always `01`.

```
# testing
qubits(2)
X(1)
CZ(0, 1)
measure()
```

Output:

```
q0: -------*---[M]---
           |
q1: -[X]---*---[M]---

Results after 100 shots (qubit 0 is the leftmost bit):
  01 | ############################## 100 (100%)
```

## Notes and limitations

- **Bit order:** in printed results, qubit 0 is the leftmost bit, matching the order of the wires in the circuit drawing.
- **Scaling:** statevector simulation stores `2^n` amplitudes in pure Python, so memory and time grow exponentially. It is comfortable up to roughly 15–20 qubits.
- **Measurement:** only measure-all at the end of the circuit is supported (no mid-circuit measurement or classical control).
- **Gates:** no parameterized rotation gates (`RX`, `RY`, `RZ`) yet.

## Ideas for future work

- Rotation gates with angle arguments, e.g. `RX(0, 1.57)`
- Toffoli (CCX) and controlled-phase gates
- Mid-circuit measurement and classical registers
- Noise models (depolarizing, bit-flip) for studying error behavior
- A basic circuit optimizer / transpiler pass (gate cancellation, depth reduction)

## Files

```
qbasic.py   the language: tokenizer, parser, simulator, and drawer
bell.q      Bell state example
random.q    basic gate test
README.md   this file
```
