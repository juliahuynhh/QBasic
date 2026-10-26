"""
QBasic - a simple quantum programming language

HOW TO RUN
    python qbasic.py              runs the built-in demo
    python qbasic.py bell.q       runs a program file

THE LANGUAGE (one command per line, '#' starts a comment)
    qubits(2)        how many qubits (must come first)
    H(0)             put a gate on a qubit (numbering starts at 0)
    CNOT(0, 1)       two-qubit gate: control first, then target
    shots(100)       (optional) how many times to run the circuit
    measure()        measure all qubits (must come last)

GATES
    H  (superposition)   X  (flip 0<->1)   Y   Z   S   T
    CNOT (flip target if control is 1)     CZ   SWAP

The program goes through 4 steps:  tokenize -> parse -> simulate -> draw
"""
import cmath
import math
import random
import re
import sys


class SimpleQError(Exception):
    pass

################################## GATES #######################################
R = 1 / math.sqrt(2)
SINGLE_QUBIT_GATES = {          # each gate is a 2x2 matrix
    "H": [[R, R], [R, -R]],
    "X": [[0, 1], [1, 0]],
    "Y": [[0, -1j], [1j, 0]],
    "Z": [[1, 0], [0, -1]],
    "S": [[1, 0], [0, 1j]],
    "T": [[1, 0], [0, cmath.exp(1j * math.pi / 4)]],
}
TWO_QUBIT_GATES = {"CNOT", "CZ", "SWAP"}


################################## STEP 1: TOKENIZE #######################################
# A "token" is the smallest meaningful piece: a word, a number, or ( ) ,
TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<word>[A-Za-z_]\w*)|(?P<number>\d+)|(?P<punct>[(),])|(?P<bad>\S))"
)


def tokenize(source):
    """Turn each line into a list of (kind, text) tokens. Comments are dropped.
    Example:  "CNOT(0, 1)"  ->  word CNOT, punct (, number 0, punct ',', number 1, punct )
    """
    lines = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        line = line.split("#")[0]
        tokens = []
        for match in TOKEN_PATTERN.finditer(line):
            kind = match.lastgroup
            if kind == "bad":
                raise SimpleQError(
                    f"line {line_number}: unexpected character '{match.group('bad')}'")
            tokens.append((kind, match.group(kind)))
        if tokens:
            lines.append((line_number, tokens))
    return lines


################################## STEP 2: PARSE #######################################
def parse(token_lines):
    """Check that each line looks like NAME(number, number, ...) and build the
    program: number of qubits, a list of gates, shots, and whether to measure."""
    n_qubits = None
    shots = 100
    gates = []        
    measured = False

    for number, tokens in token_lines:
        def fail(message):
            raise SimpleQError(f"line {number}: {message}")

        kind, name = tokens[0]
        if kind != "word":
            fail(f"a line should start with a command name, not '{name}'")
        command = name.upper()
        rest = tokens[1:]

        # shape check:  NAME  (  ...  )
        if not rest or rest[0][1] != "(":
            fail(f"commands need parentheses, like {name}(...)")
        if rest[-1][1] != ")":
            fail("missing the closing ')'")

        # read the numbers between the parentheses: 0   or   0, 1
        inside = rest[1:-1]
        numbers = []
        want_number = True
        for kind, text in inside:
            if want_number:
                if kind != "number":
                    fail(f"expected a number, got '{text}'")
                numbers.append(int(text))
            elif text == ")":
                fail("there is an extra ')'")
            elif text != ",":
                fail(f"expected ',' between numbers, got '{text}'")
            want_number = not want_number
        if inside and want_number:
            fail("there is an extra ',' before the ')'")

        if command == "QUBITS":
            if len(numbers) != 1 or numbers[0] < 1:
                fail("write it like:  qubits(2)")
            n_qubits = numbers[0]
        elif command == "SHOTS":
            if len(numbers) != 1 or numbers[0] < 1:
                fail("write it like:  shots(100)")
            shots = numbers[0]
        elif command == "MEASURE":
            if numbers:
                fail("measure takes nothing inside the parentheses:  measure()")
            measured = True
        elif command in SINGLE_QUBIT_GATES or command in TWO_QUBIT_GATES:
            if n_qubits is None:
                fail("start your program with:  qubits(N)")
            if measured:
                fail("gates must come before measure()")
            wanted = 1 if command in SINGLE_QUBIT_GATES else 2
            if len(numbers) != wanted:
                fail(f"{command} needs {wanted} qubit number(s), got {len(numbers)}")
            for q in numbers:
                if not 0 <= q < n_qubits:
                    fail(f"qubit {q} doesn't exist (you have qubits 0 to {n_qubits - 1})")
            if len(set(numbers)) != len(numbers):
                fail(f"{command} needs two different qubits")
            gates.append((command, *numbers))
        else:
            fail(f"I don't know the command '{name}'")

    if n_qubits is None:
        raise SimpleQError("your program needs a line like:  qubits(2)")
    return n_qubits, gates, shots, measured

################################## STEP 3: SIMULATE #######################################
def simulate(n_qubits, gates):
    """Track the amplitude of every possible bit pattern; apply each gate."""
    size = 2 ** n_qubits
    state = [0j] * size
    state[0] = 1                      # start in |000...0>

    for gate in gates:
        name, *qs = gate
        if name in SINGLE_QUBIT_GATES:
            (m00, m01), (m10, m11) = SINGLE_QUBIT_GATES[name]
            bit = 1 << qs[0]
            for i in range(size):
                if not i & bit:       # i has qubit=0, i|bit has qubit=1
                    a, b = state[i], state[i | bit]
                    state[i] = m00 * a + m01 * b
                    state[i | bit] = m10 * a + m11 * b
        elif name == "CNOT":
            control, target = 1 << qs[0], 1 << qs[1]
            for i in range(size):
                if i & control and not i & target:
                    state[i], state[i | target] = state[i | target], state[i]
        elif name == "CZ":
            both = (1 << qs[0]) | (1 << qs[1])
            for i in range(size):
                if i & both == both:
                    state[i] = -state[i]
        elif name == "SWAP":
            a, b = 1 << qs[0], 1 << qs[1]
            for i in range(size):
                if i & a and not i & b:
                    j = i ^ a ^ b
                    state[i], state[j] = state[j], state[i]
    return state


def measure(state, n_qubits, shots):
    """Run the circuit `shots` times, picking outcomes by their probability."""
    probabilities = [abs(amp) ** 2 for amp in state]
    picks = random.choices(range(len(state)), weights=probabilities, k=shots)
    counts = {}
    for index in picks:
        # write qubit 0 first, so the text reads in the same order as the drawing
        bits = "".join(str((index >> q) & 1) for q in range(n_qubits))
        counts[bits] = counts.get(bits, 0) + 1
    return dict(sorted(counts.items()))


################################## STEP 4: DRAW #######################################
def draw(n_qubits, gates, measured):
    """Draw the circuit as text. Each gate gets its own 5-character column."""
    n_rows = 2 * n_qubits - 1                       # wires + gaps between them
    rows = [f"q{q}: " if r == 2 * q else "    "
            for r in range(n_rows) for q in [r // 2]]
    steps = list(gates) + ([("MEASURE",)] if measured else [])

    for step in steps:
        name, *qs = step
        col = ["-----" if r % 2 == 0 else "     " for r in range(n_rows)]

        if name == "MEASURE":
            for q in range(n_qubits):
                col[2 * q] = "-[M]-"
        elif name in SINGLE_QUBIT_GATES:
            col[2 * qs[0]] = f"-[{name}]-"
        else:
            top, bottom = min(qs), max(qs)
            for r in range(2 * top + 1, 2 * bottom):       # vertical line
                col[r] = "  |  " if r % 2 else "--|--"
            if name == "CNOT":
                col[2 * qs[0]], col[2 * qs[1]] = "--*--", "-(+)-"
            elif name == "CZ":
                col[2 * qs[0]] = col[2 * qs[1]] = "--*--"
            elif name == "SWAP":
                col[2 * qs[0]] = col[2 * qs[1]] = "--x--"

        rows = [row + c for row, c in zip(rows, col)]

    return "\n".join(r + ("--" if i % 2 == 0 else "") for i, r in enumerate(rows))


def histogram(counts):
    total = sum(counts.values())
    biggest = max(counts.values())
    lines = []
    for bits, n in counts.items():
        bar = "#" * max(1, round(30 * n / biggest))
        lines.append(f"  {bits} | {bar} {n} ({100 * n / total:.0f}%)")
    return "\n".join(lines)


################################## MAIN #######################################
def run(source):
    n_qubits, gates, shots, measured = parse(tokenize(source))
    print(draw(n_qubits, gates, measured))
    if measured:
        state = simulate(n_qubits, gates)
        counts = measure(state, n_qubits, shots)
        print(f"\nResults after {shots} shots (qubit 0 is the leftmost bit):")
        print(histogram(counts))


DEMO = """
# Bell state: two qubits that always agree
qubits(2)
H(0)
CNOT(0, 1)
shots(200)
measure()
"""

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            with open(sys.argv[1], encoding="utf-8") as f:
                run(f.read())
        else:
            print("(no file given - running the demo)\n")
            run(DEMO)
    except (SimpleQError, OSError) as error:
        print("error:", error)
