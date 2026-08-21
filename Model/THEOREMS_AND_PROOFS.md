# Theorems and proofs

## Theorem 1. Closed-form Stage-1 optimum

Let all path coefficients, source coefficients, and demands be nonnegative. Let route assignments be fixed, and assume that the model contains no discrete activation, minimum-delivery, storage, or other inter-period coupling constraints. Then the Stage-1 optimum is

$$
\lambda^{\ast}=\min\left\lbrace
1,
\min_{k:L_k^s>0}\frac{Q_k}{L_k^s},
\min_{k,e:L_{ke}^e>0}\frac{C_{ke}}{L_{ke}^e}
\right\rbrace.
$$

### Proof

For every active record $r_{kf}\ge\lambda$. Since all coefficients are nonnegative,

$$
\sum_f b_{kf}d_{kf}r_{kf}\ge\lambda\sum_f b_{kf}d_{kf}=\lambda L_k^s.
$$

The source constraint therefore implies $\lambda\le Q_k/L_k^s$ whenever $L_k^s>0$. Similarly,

$$
\sum_f A_{kef}d_{kf}r_{kf}\ge\lambda L_{ke}^e,
$$

so every positive-load edge implies $\lambda\le C_{ke}/L_{ke}^e$. The upper bounds $r_{kf}\le1$ also imply $\lambda\le1$. Hence every feasible $\lambda$ is no larger than the stated minimum.

Conversely, set all active ratios equal to that minimum. Each source load becomes $\lambda^{\ast}L_k^s\le Q_k$, each edge load becomes $\lambda^{\ast}L_{ke}^e\le C_{ke}$, and $0\le\lambda^{\ast}\le1$. Thus the common-ratio vector is feasible, so the upper bound is attained. $\square$

## Theorem 2. Operator-balance equivalence and unique gross flows

Let $G=(V,E)$ be a directed tree rooted at $s$, and let each $v\ne s$ have unique incoming edge $e_v$. If $0<\eta_{ke}\le1$, then for every period $k$ and every terminal-withdrawal vector $y_k$, the node-balance system

$$
\eta_{k e_v}B_{k e_v}-\sum_{e\in\delta^+(v)}B_{ke}=y_{kv},\qquad v\ne s,
$$

has a unique solution. Moreover,

$$
B_k=M_k^{-1}y_k,
$$

and, when $y_k=P D_k r_k$,

$$
A_k=M_k^{-1}P,
\qquad
B_k=A_kD_kr_k.
$$

### Proof

Order non-source nodes from leaves towards the source and order the columns by their incoming edges. In this order, row $v$ has diagonal entry $\eta_{k e_v}>0$ and possible off-diagonal entries $-1$ only in columns associated with children of $v$, which occur earlier in the order. Therefore $M_k$ is triangular and

$$
\det M_k=\prod_{v\ne s}\eta_{k e_v}>0.
$$

Thus $M_k$ is nonsingular and the node-balance solution is unique.

For a leaf $v$, balance gives $B_{k e_v}=y_{kv}/\eta_{k e_v}$. Suppose the path-product expression holds for every child subtree of an internal node $v$. Dividing the balance equation

$$
\eta_{k e_v}B_{k e_v}=y_{kv}+\sum_{e\in\delta^+(v)}B_{ke}
$$

by $\eta_{k e_v}$ appends the factor $\eta_{k e_v}^{-1}$ to every downstream path product. Induction from the leaves to the source therefore yields exactly the loss-aware path coefficients. Since the node-balance solution is unique, the path operator and the matrix solution coincide. Substituting $y_k=P D_k r_k$ gives $A_k=M_k^{-1}P$. $\square$

## Proposition 1. Monotonicity, continuity, and concavity of the Stage-1 value

Let the positive-load resources be indexed by $j$, with normalized capacities $\xi_j=c_j/L_j$. Then

$$
\lambda^{\ast}(\xi)=\min\lbrace1,\xi_1,\ldots,\xi_m\rbrace.
$$

Consequently, $\lambda^{\ast}$ is componentwise nondecreasing, continuous, concave, and piecewise linear. Nondifferentiability occurs only at bottleneck-switch surfaces where two or more active affine pieces coincide.

## Corollary 1. Stage-2 Pareto efficiency

If all service weights are strictly positive, every Stage-2 optimum is Pareto efficient with respect to the vector of seasonal delivered volumes

$$
X_f(r)=\sum_k d_{kf}r_{kf}.
$$

Otherwise, a feasible allocation that weakly increases all $X_f$ and strictly increases at least one would strictly increase the positive weighted sum, contradicting Stage-2 optimality.

## Corollary 2. Preservation under Stage 3

If Stage 3 enforces the exact Stage-1 floor and exact Stage-2 optimum, then its solution remains Stage-2 optimal and therefore Pareto efficient. Its temporal variation is no larger than the variation of the Stage-2 allocation used as a feasible starting point.

## Novelty boundary

The results above are model-specific analytical properties. Generalized flows with gains/losses, max-min fairness, and positive-weight Pareto efficiency are established concepts in the literature. The contribution is the exact derivation and verification of these properties for the proposed deterministic loss-aware, capacity-constrained, three-stage tree-allocation model; it is not claimed as a new universal theorem of network-flow theory.
