import argparse
import time
from pathlib import Path

from .config import SEED
from .generate import Simulation

p = argparse.ArgumentParser(description="Generate the simulated buy-to-let marketplace extracts.")
p.add_argument("--scale", type=float, default=1.0, help="volume multiplier (0.25 for a quick run)")
p.add_argument("--seed", type=int, default=SEED)
p.add_argument("--out", type=Path, default=Path("data"))
a = p.parse_args()
t = time.time()
counts = Simulation(seed=a.seed, scale=a.scale, out=a.out).run()
for k, v in counts.items():
    print(f"  {k:28s} {v:>9,}")
print(f"written to {a.out}/ in {time.time() - t:.1f}s")
