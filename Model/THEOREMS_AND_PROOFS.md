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

The Stage-1 optimal set is exactly

$$
\mathcal R_1^{\ast}=\lbrace r\in\mathcal R:\ r_{kf}\ge\lambda^{\ast}\ \text{for }(k,f)\in\mathcal I\rbrace ,
$$

the canonical vector $r^{\mathrm{can}}_{kf}=\lambda^{\ast}$ on $\mathcal I$ (zero off $\mathcal I$) is its componentwise least and hence unique componentwise-minimal element, and every $r\in\mathcal R_1^{\ast}$ satisfies $\min_{(k,f)\in\mathcal I}r_{kf}=\lambda^{\ast}$.

### Proof

*Upper bound.* For every feasible pair $(r,\lambda)$ and every active record $r_{kf}\ge\lambda$. Since all coefficients are nonnegative,

$$
\sum_f b_{kf}d_{kf}r_{kf}\ge\lambda\sum_f b_{kf}d_{kf}=\lambda L_k^s.
$$

The source constraint therefore implies $\lambda\le Q_k/L_k^s$ whenever $L_k^s>0$. Similarly,

$$
\sum_f A_{kef}d_{kf}r_{kf}\ge\lambda L_{ke}^e,
$$

so every positive-load edge implies $\lambda\le C_{ke}/L_{ke}^e$. The upper bounds $r_{kf}\le1$ also imply $\lambda\le1$. Hence every feasible $\lambda$ is no larger than the stated minimum.

*Attainment.* Set all active ratios equal to that minimum and all inactive ratios to zero. Each source load becomes $\lambda^{\ast}L_k^s\le Q_k$, each edge load becomes $\lambda^{\ast}L_{ke}^e\le C_{ke}$, and $0\le\lambda^{\ast}\le1$, so the bound is attained.

*Zero-demand records and zero-load resources.* A record with $d_{kf}=0$ contributes to no load and its ratio is fixed to zero, so it can neither raise nor lower the guarantee and is excluded from the minimum. A resource with $L_j=0$ carries no flow at full demand and hence none at any $r\le\mathbf 1$; its constraint holds for every admissible $r$ and no ratio $c_j/L_j$ is formed for it.

*Optimal set.* If $(r,\lambda)$ is Stage-1 optimal then $\lambda=\lambda^{\ast}$ and $r_{kf}\ge\lambda^{\ast}$ on $\mathcal I$, so $r\in\mathcal R_1^{\ast}$. Conversely, for $r\in\mathcal R_1^{\ast}$ the pair $(r,\lambda^{\ast})$ is feasible and attains the optimum. The minimum is attained: with $\mu=\min_{\mathcal I}r_{kf}$ the pair $(r,\mu)$ is feasible, so $\mu>\lambda^{\ast}$ would contradict optimality.

*Least element.* Every $r\in\mathcal R_1^{\ast}$ satisfies $r\ge r^{\mathrm{can}}$ componentwise, on $\mathcal I$ because $r_{kf}\ge\lambda^{\ast}$ and off $\mathcal I$ because both vanish. A least element of a partially ordered set is its unique minimal element: if $\tilde r$ is minimal then $r^{\mathrm{can}}\le\tilde r$ and minimality forces equality. $\square$

**Bottleneck identification (checked numerically).** Every resource $j$ with $c_j/L_j=\lambda^{\ast}$ is tight at every Stage-1 optimal allocation, because $B_j(r)\ge\lambda^{\ast}L_j=c_j$ for $r\in\mathcal R_1^{\ast}$. The randomized suite checks this at the Stage-1 LP and Stage-3 optima, and confirms the diagnosis with the Stage-1 LP alone: relaxing every other resource leaves the LP value unchanged, relaxing the named resources raises it.

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

**Dimensions.** With $n_V=|V|-1$ and $n_F=|F|$, $M_k\in\mathbb R^{n_V\times n_V}$ has rows and columns indexed by the non-source nodes, each identified with its incoming edge; $P\in\lbrace0,1\rbrace^{n_V\times n_F}$ has $P_{vf}=1$ exactly when $v$ is the withdrawal node of user $f$; $A_k\in\mathbb R^{n_V\times n_F}$.

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

**Users at nonterminal nodes.** The identity $A_k=M_k^{-1}P$ needs only that every user be attached to exactly one node and that every non-source node have one incoming edge; a withdrawal at a junction is a 1 in the corresponding row of $P$. What cannot be relaxed is single-route service.

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

## Remark 2. When Stage 3 is redundant (manuscript Section 3.3)

Let $\mathcal R_2^{\ast}$ be the Stage-2 optimal face. Stage 3 changes the temporal variation of a Stage-2 optimum $r^{(2)}$ only if $\Omega$ is not constant on $\mathcal R_2^{\ast}$; in particular, if $\mathcal R_2^{\ast}$ is a single point, then $r^{(3)}=r^{(2)}$ and Stage 3 is redundant. The face is a single point whenever the Stage-2 objective is not parallel to any face of $\mathcal R_1^{\ast}$ of positive dimension, which is the generic case for heterogeneous weights and efficiencies; ties in $w_fd_{kf}$ relative to the route coefficients of a binding resource, as produced by uniform weights and a small number of lining classes, create a face of positive dimension.

### Proof

If $\mathcal R_2^{\ast}=\lbrace r^{(2)}\rbrace$ the Stage-3 feasible set in $r$ is that single point. If $\Omega$ is constant on $\mathcal R_2^{\ast}$ then every Stage-2 optimum already attains $\Omega^{\ast}$. $\square$

The randomized suite tests the face for being a single point by maximizing and minimizing a random linear functional over $\mathcal R_2^{\ast}$ and classifies each instance as Stage 3 active, redundant (single point), or inactive at the solver vertex.

## Novelty boundary

The results above are model-specific analytical properties. Generalized flows with gains/losses, max-min fairness, and positive-weight Pareto efficiency are established concepts in the literature. The contribution is the exact derivation and verification of these properties for the proposed deterministic loss-aware, capacity-constrained, three-stage tree-allocation model; it is not claimed as a new universal theorem of network-flow theory.
