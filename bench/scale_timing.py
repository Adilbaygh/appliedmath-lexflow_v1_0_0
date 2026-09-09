"""Runtime/memory check for the Appendix A scaling generator.

Closed-form Stage-1 (Theorem 1) vs. sparse HiGHS Stage-1 LP.
Timings are the MINIMUM over repeated runs after a warm-up, which is the
standard way of suppressing operating-system scheduling noise; the minimum is
the most reproducible statistic on a loaded desktop machine."""
import math, time, tracemalloc
import numpy as np
from scipy.sparse import coo_matrix
from scipy.optimize import linprog

ETA = (0.99, 0.98, 0.97, 0.96)
RHO = (0.90, 0.80, 0.70, 0.60)
K = 4

def build(F):
    m = math.ceil(math.log2(F)); P = 2**m
    # heap-indexed complete binary tree, root = node 1 (source)
    nodes = 2*P - 1
    leaves = list(range(P, 2*P))          # heap indices of leaves
    users = leaves[:F]
    # edges: (parent -> child) for child = 2..2P-1 ; edge id = child index
    E = list(range(2, nodes+1))
    eidx = {c: i for i, c in enumerate(E)}
    # path of user f = edges from root to its leaf
    paths = []
    for u in users:
        p, c = [], u
        while c > 1:
            p.append(eidx[c]); c //= 2
        paths.append(p[::-1])             # root -> leaf order
    d = np.array([[20 + ((7*(f+1) + 11*(k+1)) % 31) for f in range(F)] for k in range(K)], float)
    return m, len(E), paths, d

def closed_form(F):
    m, nE, paths, d = build(F)
    lam = 1.0
    for k in range(K):
        inv = 1.0/ETA[k]
        b = inv**m
        Lsrc = float((b*d[k]).sum())
        Q = RHO[k]*Lsrc
        if Lsrc > 0: lam = min(lam, Q/Lsrc)
        Le = np.zeros(nE)
        for f, p in enumerate(paths):
            L = len(p)
            for pos, e in enumerate(p):
                Le[e] += inv**(L-pos) * d[k, f]      # edges from e to terminal
        C = 1.2*Le
        pos = Le > 0
        if pos.any(): lam = min(lam, float((C[pos]/Le[pos]).min()))
    return lam, nE

def lp(F):
    m, nE, paths, d = build(F)
    n = K*F
    rows, cols, vals, ub = [], [], [], []
    R = 0
    for k in range(K):
        inv = 1.0/ETA[k]; b = inv**m
        for f in range(F):
            rows.append(R); cols.append(k*F+f); vals.append(b*d[k, f])
        ub.append(RHO[k]*float((b*d[k]).sum())); R += 1
        Le = np.zeros(nE)
        for f, p in enumerate(paths):
            L = len(p)
            for pos_, e in enumerate(p):
                a = inv**(L-pos_)
                rows.append(R+e); cols.append(k*F+f); vals.append(a*d[k, f])
                Le[e] += a*d[k, f]
        ub.extend(list(1.2*Le)); R += nE
    for i in range(n):                       # lambda - r_i <= 0
        rows.append(R+i); cols.append(i);  vals.append(-1.0)
        rows.append(R+i); cols.append(n);  vals.append(1.0)
        ub.append(0.0)
    R += n
    A = coo_matrix((vals, (rows, cols)), shape=(R, n+1)).tocsr()
    c = np.zeros(n+1); c[n] = -1.0
    res = linprog(c, A_ub=A, b_ub=np.array(ub),
                  bounds=[(0, 1)]*(n+1), method="highs")
    return -res.fun, R

N_CF, N_LP = 40, 15          # repetitions; the reported time is the minimum

print(f"{'F':>5} {'|E|':>6} {'|I|':>6} {'rows':>7} {'cf lambda*':>12} {'LP lambda*':>12} "
      f"{'|diff|':>10} {'cf ms':>9} {'LP ms':>9} {'cf MiB':>8} {'LP MiB':>8}")
print("(times = minimum over %d / %d repetitions after warm-up)" % (N_CF, N_LP))
out=[]
for F in (20, 50, 100, 250, 500):
    for _ in range(3): closed_form(F); lp(F)          # warm-up
    best = float("inf")
    for _ in range(N_CF):
        t = time.perf_counter(); lam_cf, nE = closed_form(F)
        best = min(best, (time.perf_counter()-t)*1000)
    t_cf = best
    best = float("inf")
    for _ in range(N_LP):
        t = time.perf_counter(); lam_lp, rows = lp(F)
        best = min(best, (time.perf_counter()-t)*1000)
    t_lp = best
    tracemalloc.start(); closed_form(F); m_cf = tracemalloc.get_traced_memory()[1]/2**20; tracemalloc.stop()
    tracemalloc.start(); lp(F);          m_lp = tracemalloc.get_traced_memory()[1]/2**20; tracemalloc.stop()
    print(f"{F:>5} {nE:>6} {K*F:>6} {rows:>7} {lam_cf:>12.10f} {lam_lp:>12.10f} "
          f"{abs(lam_cf-lam_lp):>10.2e} {t_cf:>9.3f} {t_lp:>9.2f} {m_cf:>8.2f} {m_lp:>8.2f}")
