#!/usr/bin/env python3
"""frontend/host.py -- Generate .mal programs using congruence technique.

Usage:
    python host.py gen --ops "/</</<v"           # from opcode chars
    python host.py gen --text "Hello"              # from desired output
    python host.py gen --ops "/</v" --output out.mal
    python host.py list-ops                        # show available opcodes
"""

import argparse
import sys
from pathlib import Path

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

OPCODES = {
    "IN": "/", "OUT": "<", "HALT": "v",
    "CRAZY": "p", "ROT": "*", "MOVD": "j", "BRANCH": "i",
}


def encode(inst_chars: list[str]) -> str:
    """Encode instruction characters to Malbolge source via congruence."""
    return "".join(
        chr((XLAT1.index(ch) - i) % 94 + 33)
        for i, ch in enumerate(inst_chars)
    )


def decode(source: str) -> str:
    """Decode Malbolge source to instruction characters."""
    return "".join(
        XLAT1[(ord(ch) - 33 + i) % 94]
        for i, ch in enumerate(source)
    )


def gen_echo(n: int) -> list[str]:
    """Generate IN, OUT sequence for n characters."""
    ops = []
    for _ in range(n):
        ops.extend(["/", "<"])
    ops.append("v")
    return ops


def gen_passthrough() -> list[str]:
    """Read all input, output all, then halt. Simple cat."""
    return ["/", "<", "v"]  # single char echo


def cmd_gen(args):
    if args.ops:
        chars = list(args.ops)
    elif args.text:
        # Generate echo program for each character
        chars = []
        for _ in args.text:
            chars.extend(["/", "<"])
        chars.append("v")
    elif args.echo:
        chars = gen_echo(args.echo)
    else:
        print("Specify --ops, --text, or --echo", file=sys.stderr)
        sys.exit(1)

    src = encode(chars)

    if args.output:
        Path(args.output).write_text(src, encoding="ascii")
        print(f"Written: {args.output} ({len(src)} bytes)", file=sys.stderr)
    else:
        print(src)


def cmd_decode(args):
    source = args.source
    result = decode(source)
    for i, ch in enumerate(source):
        ix = (ord(ch) - 33 + i) % 94
        inst = XLAT1[ix]
        print(f"  [{i}] {ch!r} idx={ix} -> {inst!r}")


def cmd_list_ops(args):
    print("Available opcodes:")
    for name, char in OPCODES.items():
        idx = XLAT1.index(char)
        print(f"  {name:10s} char={char!r}  XLAT1 index={idx}")


def main():
    parser = argparse.ArgumentParser(description="Malbolge frontend (generator)")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("gen")
    p.add_argument("--ops", help="Opcode chars, e.g. '/</</<v'")
    p.add_argument("--text", help="Text to output (generates echo)")
    p.add_argument("--echo", type=int, help="Echo N chars from stdin")
    p.add_argument("--output", "-o", help="Output file")

    p = sub.add_parser("decode")
    p.add_argument("source", help="Malbolge source to decode")

    p = sub.add_parser("list-ops")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "decode":
        cmd_decode(args)
    elif args.cmd == "list-ops":
        cmd_list_ops(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
