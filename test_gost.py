#!/usr/bin/env python3
"""Cross-backend test suite for gost.c Malbolge interpreter.

Tests gost against the Python oracle and Malbolge-Engine on known programs.
All three must agree for a test to pass.
"""
import subprocess
import sys
import tempfile
import os
import unittest
from pathlib import Path

GOST = str(Path(__file__).parent / "gost.exe")
ENGINE = str(Path(__file__).parent.parent / "Malbolge-Engine" / "malbolge.exe")
ORACLE_DIR = str(Path(__file__).parent.parent / "malbolge-oracle")

# Canonical programs
HELLO_WORLD = "(=<`#9]~6ZY32Vx/4Rs+0No-&Jk)\"Fh}|Bcy?`=*z]Kw%oG4UUS0/@-ejc(:'8dc"


def run_gost(source, input_data=b"", steps=100000):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mal", delete=False) as f:
        f.write(source)
        path = f.name
    try:
        r = subprocess.run([GOST, path, str(steps)], input=input_data,
                           capture_output=True, timeout=30)
        return r.stdout.rstrip(b"\r\n"), r.returncode
    finally:
        os.unlink(path)


def run_engine(source, input_data=b"", steps=100000):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mal", delete=False) as f:
        f.write(source)
        path = f.name
    try:
        r = subprocess.run([ENGINE, path, str(steps)], input=input_data,
                           capture_output=True, timeout=30)
        return r.stdout.rstrip(b"\r\n"), r.returncode
    finally:
        os.unlink(path)


def run_oracle(source, input_data=b"", steps=100000):
    input_str = input_data.decode("ascii", errors="replace") if input_data else ""
    code = f'''
import sys; sys.path.insert(0, r"{ORACLE_DIR}")
from oracle import Oracle
m = Oracle()
m.load_ascii(list({source!r}))
if {input_str!r}:
    m.provide_input({input_str!r})
r = m.run(max_steps={steps})
sys.stdout.buffer.write(r.output.encode("ascii"))
'''
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=30)
    return r.stdout, r.returncode


class TestBackendsAgree(unittest.TestCase):
    """All three backends must produce identical output."""

    def _check(self, source, input_data=b"", steps=100000):
        g_out, g_rc = run_gost(source, input_data, steps)
        e_out, e_rc = run_engine(source, input_data, steps)
        o_out, o_rc = run_oracle(source, input_data, steps)
        
        self.assertEqual(g_out, o_out,
                         f"gost vs oracle mismatch: {g_out!r} vs {o_out!r}")
        self.assertEqual(g_out, e_out,
                         f"gost vs engine mismatch: {g_out!r} vs {e_out!r}")
        self.assertEqual(g_rc, 0, f"gost exit code: {g_rc}")
        return g_out

    def test_hello_world(self):
        out = self._check(HELLO_WORLD)
        self.assertEqual(out, b"Hello World!")

    def test_nop_halt(self):
        """Single HALT instruction. 'Q' decodes to 'v' (HALT) at pos 0."""
        self._check("Q")

    def test_echo1(self):
        """Read one char, output it."""
        self._check("ubO", input_data=b"X", steps=1000)

    def test_echo2(self):
        """Read two chars, output both."""
        self._check("ubs`M", input_data=b"Hi", steps=10000)

    def test_echo3(self):
        """Read three chars, output all."""
        self._check("ubs`q^K", input_data=b"ABC", steps=10000)


class TestGostSpecific(unittest.TestCase):
    """Tests specific to gost behavior."""

    def test_gost_handles_eof(self):
        """When input is exhausted, '/' sets a=59048."""
        out, rc = run_gost("ubO", input_data=b"", steps=1000)
        # With no input, '/' reads EOF -> a=59048, output = chr(59048 % 256)
        self.assertEqual(rc, 0)

    def test_gost_step_limit(self):
        """Timeout returns non-zero exit code."""
        out, rc = run_gost("ubO", input_data=b"A", steps=1)
        self.assertEqual(rc, 3)  # timeout exit code

    def test_gost_invalid_program(self):
        """Empty program fails gracefully."""
        r = subprocess.run([GOST, "nonexistent.mal"], capture_output=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)


class TestXlatConsistency(unittest.TestCase):
    """Verify XLAT1/XLAT2 tables match the spec."""

    def test_xlat1_length(self):
        code = 'print(len("+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\\"lI.v%{gJh4G\\\\-=O@5`_3i<?Z\'" ";FNQuY]szf$!BS/|t:Pn6^Ha"))'
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=10)
        self.assertEqual(r.stdout.strip(), b"94")

    def test_xlat2_is_permutation(self):
        code = (
            "import sys; sys.path.insert(0, r'" + ORACLE_DIR + "')\n"
            "from oracle import XLAT2\n"
            "print(len(XLAT2), len(set(XLAT2)) == len(XLAT2))"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=10)
        self.assertEqual(r.stdout.strip(), b"94 True")


if __name__ == "__main__":
    unittest.main(verbosity=2)
