# Deterministic lexicographic flow allocation on lossy capacitated trees

## 1. Scope

The model is deterministic. All demands, source limits, edge capacities, efficiencies, assignments, periods, and weights are fixed inputs. No scenario index, uncertainty set, probability distribution, robust counterpart, recourse decision, or chance constraint is used.

## 2. Rooted tree

Let $G=(V,E)$ be a directed tree rooted at source $s$. Every $v\ne s$ has a unique incoming edge $e_v=(p(v),v)$. Edges point from the source towards terminal nodes $T\subseteq V$.

Sets:

- $K$: ordered planning periods;
- $F$: service blocks;
- $\mathcal I=\lbrace(k,f):d_{kf}>0\rbrace$: active service records;
- $P_f$: unique source-to-terminal edge path for user $f$.

Fixed parameters:

- $d_{kf}\ge0$: net demand;
- $Q_k\ge0$: source gross-volume limit;
- $C_{ke}\ge0$: upstream gross edge capacity;
- $\eta_{ke}\in(0,1]$: edge conveyance efficiency;
- $w_f>0$: seasonal service weight.

Decision ratio:

$$
0\le r_{kf}\le1,\qquad (k,f)\in\mathcal I.
$$

## 3. Loss-aware path operator

For $e\in P_f$, define

$$
A_{kef}=\prod_{j\in P_f:\,j\succeq e}\eta_{kj}^{-1},
$$

and set $A_{kef}=0$ if $e\notin P_f$. The source coefficient is

$$
b_{kf}=\prod_{j\in P_f}\eta_{kj}^{-1}.
$$

Delivered net volume and required gross volumes are

$$
x_{kf}=d_{kf}r_{kf},
$$

$$
B_{ke}=\sum_{f\in F}A_{kef}d_{kf}r_{kf},
$$

$$
B_k^s=\sum_{f\in F}b_{kf}d_{kf}r_{kf}.
$$

## 4. Independent node-balance system

Let $y_{kv}$ be terminal withdrawal at node $v$. For each $v\ne s$,

$$
\eta_{k e_v}B_{k e_v}-\sum_{e\in\delta^+(v)}B_{ke}=y_{kv}.
$$

In matrix form,

$$
M_kB_k=P D_k r_k.
$$

For reverse topological ordering, $M_k$ is triangular and

$$
\det M_k=\prod_{v\ne s}\eta_{k e_v}>0.
$$

Hence

$$
B_k=M_k^{-1}P D_k r_k,
\qquad A_k=M_k^{-1}P.
$$

## 5. Physical feasible set

$$
\sum_f b_{kf}d_{kf}r_{kf}\le Q_k,\qquad k\in K,
$$

$$
\sum_f A_{kef}d_{kf}r_{kf}\le C_{ke},\qquad k\in K,\ e\in E.
$$

## 6. Stage 1: common max-min guarantee

$$
\max_{r,\lambda}\ \lambda
$$

subject to the physical constraints and

$$
r_{kf}\ge\lambda,\qquad (k,f)\in\mathcal I.
$$

Define full-demand loads

$$
L_k^s=\sum_f b_{kf}d_{kf},
\qquad
L_{ke}^e=\sum_f A_{kef}d_{kf}.
$$

Then

$$
\lambda^{\ast}=\min\left\lbrace 1,\ \min_{k:L_k^s>0}\frac{Q_k}{L_k^s},\ \min_{k,e:L_{ke}^e>0}\frac{C_{ke}}{L_{ke}^e} \right\rbrace.
$$

## 7. Stage 2: weighted seasonal satisfaction

$$
D^w=\sum_{(k,f)\in\mathcal I}w_fd_{kf},
$$

$$
S(r)=\frac{\sum_{(k,f)\in\mathcal I}w_fd_{kf}r_{kf}}{D^w}.
$$

Stage 2 solves

$$
\max_r\ S(r)
$$

subject to the physical constraints and the exact theoretical floor

$$
r_{kf}\ge\lambda^{\ast}.
$$

## 8. Stage 3: exact lexicographic temporal selector

For adjacent planning periods for which both service records are active,

$$
\Omega(r)=\sum_{(k,f)\in\mathcal J}|r_{kf}-r_{k-1,f}|.
$$

Stage 3 solves

$$
\min_r\ \Omega(r)
$$

subject to the physical constraints,

$$
r_{kf}\ge\lambda^{\ast},
$$

and exact preservation of the Stage-2 optimum,

$$
S(r)=\theta^{\ast}.
$$

In floating-point implementation, the equality is enforced within a declared numerical tolerance; the tolerance is not a model parameter.

## 9. Main analytical properties

1. All three stages possess an optimum because their feasible sets are nonempty, closed, and bounded.
2. Stage 1 has the closed-form value stated above.
3. The path operator and node-balance system are equivalent on a rooted tree.
4. The induced edge-flow vector is unique for every delivery vector.
5. $\lambda^{\ast}$ is componentwise nondecreasing in $Q$ and $C$.
6. As a function of normalized capacities, $\lambda^{\ast}$ is continuous, concave, and piecewise linear.
7. With positive $w_f$, every Stage-2 optimum is Pareto efficient in seasonal delivered volumes.
8. Stage 3 preserves Stage-1 and Stage-2 optimality while weakly reducing $\Omega$.
