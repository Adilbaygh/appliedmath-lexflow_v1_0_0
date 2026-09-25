"""Runtime and memory of the closed-form Stage-1 value against the Stage-1 LP.

Instances are those of the Appendix A.1 scaling generator (F = 20 ... 500
users, four periods). Every run is split into the phases that a user of either
route actually pays for:

    build      topology, routes and demands                (shared)
    loads      full-demand gross loads L_k^src and L_ke     (shared)
    cf_scan    minimum of the capacity-to-load ratios, (25) (closed form only)
    lp_build   sparse constraint matrix of the Stage-1 LP  (LP only)
    lp_solve   HiGHS solve                                 (LP only)

so that closed form = loads + cf_scan and LP = loads + lp_build + lp_solve,
both with build excluded. Each phase is timed REPEATS times after WARMUP
warm-up runs; the CSV reports median, interquartile range and minimum.
Memory is measured separately with tracemalloc (one run each). What that
reports is the peak of the Python allocations tracemalloc itself traces: the
internal C++ allocations of HiGHS, which SciPy calls as compiled code, are
NOT included, so the figure is a like-for-like comparison of the Python side
of the two routes and not the working set of the process.

Outputs (from the repository root, ``python bench/scale_timing.py``):

    results/timing/scale_timing.csv       one row per instance size
    results/timing/scale_timing_raw.csv   every repetition of every phase
    results/timing/environment.json       CPU, OS and library versions

``results/timing`` is preserved by ``run_analysis.py`` and hashed into its
manifest; wall-clock times are machine dependent and are not part of the
byte-reproducibility test.
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "timing"

ETA = (0.99, 0.98, 0.97, 0.96)
RHO = (0.90, 0.80, 0.70, 0.60)
K = 4
SIZES = (20, 50, 100, 250, 500)
REPEATS = 30
WARMUP = 3


# --------------------------------------------------------------------------- #
#  phases
# --------------------------------------------------------------------------- #
def build(F):
    """Complete binary tree with 2**ceil(log2 F) leaves; the first F are users."""
    m = math.ceil(math.log2(F))
    P = 2 ** m
    nodes = 2 * P - 1
    users = list(range(P, 2 * P))[:F]
    E = list(range(2, nodes + 1))
    eidx = {c: i for i, c in enumerate(E)}
    paths = []
    for u in users:
        p, c = [], u
        while c > 1:
            p.append(eidx[c])
            c //= 2
        paths.append(p[::-1])
    d = np.array([[20 + ((7 * (f + 1) + 11 * (k + 1)) % 31) for f in range(F)]
                  for k in range(K)], float)
    return m, len(E), paths, d


def loads(inst):
    """Full-demand gross loads and the route coefficients (shared by both routes)."""
    m, nE, paths, d = inst
    src, edge, coeff = [], [], []
    for k in range(K):
        inv = 1.0 / ETA[k]
        b = inv ** m
        src.append(float((b * d[k]).sum()))
        Le = np.zeros(nE)
        ck = []
        for f, p in enumerate(paths):
            L = len(p)
            for pos, e in enumerate(p):
                a = inv ** (L - pos)
                Le[e] += a * d[k, f]
                ck.append((e, f, a))
        edge.append(Le)
        coeff.append((b, ck))
    return src, edge, coeff


def capacities(src, edge):
    Q = [RHO[k] * src[k] for k in range(K)]
    C = [1.2 * edge[k] for k in range(K)]
    return Q, C


def cf_scan(src, edge, Q, C):
    """Equation (25): one pass over the positive-load resources."""
    lam = 1.0
    for k in range(K):
        if src[k] > 0:
            lam = min(lam, Q[k] / src[k])
        pos = edge[k] > 0
        if pos.any():
            lam = min(lam, float((C[k][pos] / edge[k][pos]).min()))
    return lam


def lp_build(inst, coeff, Q, C):
    m, nE, paths, d = inst
    F = d.shape[1]
    n = K * F
    rows, cols, vals, ub = [], [], [], []
    R = 0
    for k in range(K):
        b, ck = coeff[k]
        for f in range(F):
            rows.append(R); cols.append(k * F + f); vals.append(b * d[k, f])
        ub.append(Q[k]); R += 1
        for e, f, a in ck:
            rows.append(R + e); cols.append(k * F + f); vals.append(a * d[k, f])
        ub.extend(list(C[k])); R += nE
    for i in range(n):                       # lambda - r_i <= 0
        rows.append(R + i); cols.append(i); vals.append(-1.0)
        rows.append(R + i); cols.append(n); vals.append(1.0)
        ub.append(0.0)
    R += n
    A = coo_matrix((vals, (rows, cols)), shape=(R, n + 1)).tocsr()
    c = np.zeros(n + 1)
    c[n] = -1.0
    return A, np.array(ub), c, R


def lp_solve(A, ub, c):
    res = linprog(c, A_ub=A, b_ub=ub, bounds=[(0, 1)] * len(c), method="highs")
    return -res.fun


# --------------------------------------------------------------------------- #
#  measurement
# --------------------------------------------------------------------------- #
def _timed(fn, *args):
    t = time.perf_counter()
    out = fn(*args)
    return out, (time.perf_counter() - t) * 1000.0


def _stats(values):
    q = statistics.quantiles(values, n=4, method="inclusive")
    return statistics.median(values), q[0], q[2], min(values)


def _cpu_name() -> str:
    try:
        if sys.platform.startswith("win"):
            # read the marketing name from the registry: no subprocess, so no
            # dependence on the console code page
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if name:
                return str(name).strip()
        elif Path("/proc/cpuinfo").exists():
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:  # pragma: no cover - best effort only
        pass
    return platform.processor() or "unknown"


def environment() -> dict[str, object]:
    return {
        "cpu": _cpu_name(),
        "logical_cpus": os.cpu_count(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "solver": "HiGHS via scipy.optimize.linprog(method='highs')",
        "timer": "time.perf_counter, single process, single thread of Python",
        "memory": ("tracemalloc peak of traced Python allocations; the internal "
                   "allocations of HiGHS are compiled code and are not traced"),
        "threads": ("the Python process is single-threaded; the number of threads "
                    "HiGHS may use is not restricted by this script and no CPU "
                    "affinity is set"),
        "repeats_per_phase": REPEATS,
        "warmup_runs": WARMUP,
        "statistics": "median, interquartile range (Q1-Q3) and minimum",
        "build_excluded": True,
    }


def measure(F):
    for _ in range(WARMUP):
        inst = build(F); src, edge, coeff = loads(inst); Q, C = capacities(src, edge)
        cf_scan(src, edge, Q, C); lp_solve(*lp_build(inst, coeff, Q, C)[:3])

    raw = {ph: [] for ph in ("build", "loads", "cf_scan", "lp_build", "lp_solve")}
    for _ in range(REPEATS):
        inst, t = _timed(build, F); raw["build"].append(t)
        (src, edge, coeff), t = _timed(loads, inst); raw["loads"].append(t)
        Q, C = capacities(src, edge)
        lam_cf, t = _timed(cf_scan, src, edge, Q, C); raw["cf_scan"].append(t)
        (A, ub, c, rows), t = _timed(lp_build, inst, coeff, Q, C); raw["lp_build"].append(t)
        lam_lp, t = _timed(lp_solve, A, ub, c); raw["lp_solve"].append(t)
    raw["cf_total"] = [a + b for a, b in zip(raw["loads"], raw["cf_scan"])]
    raw["lp_total"] = [a + b + c_ for a, b, c_ in
                       zip(raw["loads"], raw["lp_build"], raw["lp_solve"])]

    def peak(fn):
        """Peak of the Python allocations traced by tracemalloc, in MiB.

        This is not the working set of the process: allocations made inside the
        HiGHS shared library are not traced.
        """
        tracemalloc.start()
        fn()
        value = tracemalloc.get_traced_memory()[1] / 2 ** 20
        tracemalloc.stop()
        return value

    inst = build(F)

    def run_cf():
        s, e, _ = loads(inst); q, cc = capacities(s, e); cf_scan(s, e, q, cc)

    def run_lp():
        s, e, co = loads(inst); q, cc = capacities(s, e)
        lp_solve(*lp_build(inst, co, q, cc)[:3])

    row = {
        "F": F, "edges": inst[1], "active_records": K * F, "lp_rows": rows,
        "lambda_cf": lam_cf, "lambda_lp": lam_lp, "abs_difference": abs(lam_cf - lam_lp),
    }
    for ph in ("build", "loads", "cf_scan", "cf_total", "lp_build", "lp_solve", "lp_total"):
        med, q1, q3, mn = _stats(raw[ph])
        row.update({f"{ph}_median_ms": med, f"{ph}_q1_ms": q1,
                    f"{ph}_q3_ms": q3, f"{ph}_min_ms": mn})
    row["speedup_median_total"] = row["lp_total_median_ms"] / row["cf_total_median_ms"]
    row["cf_peak_traced_mib"] = peak(run_cf)
    row["lp_peak_traced_mib"] = peak(run_lp)
    return row, raw


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    env = environment()
    (OUT / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    rows, raw_rows = [], []
    for F in SIZES:
        row, raw = measure(F)
        rows.append(row)
        for ph, values in raw.items():
            for i, v in enumerate(values):
                raw_rows.append({"F": F, "phase": ph, "repeat": i + 1, "ms": v})
        print(f"F={F:>4} |E|={row['edges']:>5}  cf {row['cf_total_median_ms']:8.3f} ms "
              f"[{row['cf_total_q1_ms']:.3f}, {row['cf_total_q3_ms']:.3f}]  "
              f"LP {row['lp_total_median_ms']:8.2f} ms "
              f"[{row['lp_total_q1_ms']:.2f}, {row['lp_total_q3_ms']:.2f}]  "
              f"(solve {row['lp_solve_median_ms']:.2f})  x{row['speedup_median_total']:.1f}  "
              f"|diff| {row['abs_difference']:.1e}")
    with open(OUT / "scale_timing.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(OUT / "scale_timing_raw.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["F", "phase", "repeat", "ms"])
        w.writeheader(); w.writerows(raw_rows)
    print(f"environment: {env['cpu']} | {env['os']} | Python {env['python']} | "
          f"NumPy {env['numpy']} | SciPy {env['scipy']}")
    print(f"written: {OUT / 'scale_timing.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
