"""compiler/ir.py -- IR for Text -> Malbolge Print Program."""
from dataclasses import dataclass

@dataclass
class PrintProgram:
    text: str
    # For each char, tuple of K's that maps via CRAZYs from previous a to ord(c)
    steps: list[tuple[int, ...]]

def lookup_print_steps(text: str) -> PrintProgram:
    """Find K tuple for each char via brute force (reference Python oracle)."""
    def crazy(a,b):
        t=[1,1,2,0,0,2,0,2,1]; r=0; p=1
        for _ in range(10): r+=t[(a%3)*3+(b%3)]*p; a//=3; b//=3; p*=3
        return r
    steps=[]
    prev=0
    for ch in text:
        c=ord(ch)
        found=None
        # Try depth 2, then 3
        for depth in [2,3,4]:
            if found: break
            # Use iterative deepening over K values
            # For depth 2: 94^2=8836, depth 3: 830k, depth 4: 78M -> limit
            # For depth 3, we can brute force with pruning
            import itertools
            if depth==2:
                for K1 in range(33,127):
                    for K2 in range(33,127):
                        a=crazy(prev,K1); a=crazy(a,K2)
                        if a%256==c:
                            found=(K1,K2)
                            break
                    if found: break
            elif depth==3:
                for K1 in range(33,127):
                    for K2 in range(33,127):
                        a=crazy(prev,K1); a=crazy(a,K2)
                        for K3 in range(33,127):
                            b=crazy(a,K3)
                            if b%256==c:
                                found=(K1,K2,K3)
                                break
                        if found: break
                    if found: break
            elif depth==4:
                for K1 in range(33,127):
                    for K2 in range(33,127):
                        a=crazy(prev,K1); a=crazy(a,K2)
                        for K3 in range(33,127):
                            b=crazy(a,K3)
                            for K4 in range(33,127):
                                cc=crazy(b,K4)
                                if cc%256==c:
                                    found=(K1,K2,K3,K4)
                                    break
                            if found: break
                        if found: break
                    if found: break
        if not found:
            raise ValueError(f"No steps for {ch!r} from {prev} up to depth 4")
        steps.append(found)
        # Update prev to c (the target char's ord, not the last CRAZY result)
        prev=c
    return PrintProgram(text, steps)
