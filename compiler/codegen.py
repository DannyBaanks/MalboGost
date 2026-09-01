"""compiler/codegen.py -- Emit Malbolge print program and frontend."""
XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
def enc(inst, pos): return chr((XLAT1.index(inst)-pos)%94+33)

def emit_print_program(text: str, steps) -> str:
    """Emit Malbolge program that prints text without input (via CRAZYs per char)."""
    prog=['']*150
    prog[0]=chr((XLAT1.index('i')-0)%94+33)
    for i in range(1,99): prog[i]='A'
    # Place K's at d positions: after BRANCH, d=1 at pos99, so first CRAZY at d=1 reads prog[1], etc.
    # For text "AB" with steps [(45,74),(34,33)], need prog[1]=45, prog[2]=74, prog[4]=34, prog[5]=33
    # For "Hi" with [(33,72),(33,33,33)], need prog[1]=33,2=72,4=33,5=33,6=33 (with OUT gaps)
    d_pos=1
    for tup in steps:
        for K in tup:
            prog[d_pos]=chr(K); d_pos+=1
        d_pos+=1  # gap for OUT
    pos=99
    for tup in steps:
        for _ in tup:
            prog[pos]=enc('p',pos); pos+=1
        prog[pos]=enc('<',pos); pos+=1
    prog[pos]=enc('v',pos); pos+=1
    prog=prog[:pos]
    return ''.join(prog)

def emit_frontend(text: str) -> str:
    """Emit Malbolge frontend that reads text and outputs its print program.

    For the 2-char demo, this is a program that reads 2 chars (e.g. 'A','B')
    and does M4/M5/M6-style lookups to output the print program's source.
    Full implementation uses the per-char K1/K2 tables and outputs the
    print program via a loop of CRAZY->OUT for each output char.
    See M4/M5/M6 for the demonstrated primitives; this skeleton shows the
    structure for arbitrary text.
    """
    # Skeleton: for text "AB", frontend would be:
    #   IN, CRAZY(K=36) -> K1 for 'A', ... etc., then a series of OUTs for the print program template
    # Full codegen is the IR->Malbolge state-machine compiler (the hard sub-project).
    # For now, return a stub that would be expanded.
    return f"; Frontend for {text!r} would be generated here via the state-machine compiler\n"

if __name__=="__main__":
    from ir import lookup_print_steps
    for txt in ["A","AB","Hi"]:
        pp=lookup_print_steps(txt)
        print(txt, pp.steps)
        prog=emit_print_program(txt, pp.steps)
        print(f"  len {len(prog)}")
        # Verify with oracle
        import sys
        from pathlib import Path as _P
        sys.path.insert(0, str(_P(__file__).parent.parent.parent / "malbolge-oracle"))
        from oracle import Oracle
        o=Oracle(); o.load_ascii(list(prog)); o.provide_input(""); r=o.run(max_steps=100000)
        print(f"    verify: {r.output!r} ok={r.output==txt}")
