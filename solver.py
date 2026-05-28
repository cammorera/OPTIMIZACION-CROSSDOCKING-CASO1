"""
Cross-Docking MIP Solver
Minimizes makespan (T) for scheduling inbound/outbound trucks.
"""

import pulp
from typing import Dict, Tuple, List


# ─────────────────────────────────────────────
#  DATA PARSER
# ─────────────────────────────────────────────

def parse_data(text: str) -> Tuple[List, List, List, Dict, Dict]:
    """
    Parse instance file with format:
        i <n_inbound>  o <n_outbound>  n <n_products>
        r <i> <k> <qty>   ...
        s <j> <k> <qty>   ...
    Returns (I, J, K, r, s).
    """
    tokens = text.split()
    idx = 0

    def consume(label):
        nonlocal idx
        assert tokens[idx] == label, f"Expected '{label}', got '{tokens[idx]}'"
        val = int(tokens[idx + 1])
        idx += 2
        return val

    n_i = consume("i")
    n_j = consume("o")
    n_k = consume("n")

    I = list(range(1, n_i + 1))
    J = list(range(1, n_j + 1))
    K = list(range(1, n_k + 1))

    r = {(i, k): 0 for i in I for k in K}
    s = {(j, k): 0 for j in J for k in K}

    while idx < len(tokens):
        typ = tokens[idx]
        if typ == "r":
            i, k, v = int(tokens[idx+1]), int(tokens[idx+2]), int(tokens[idx+3])
            r[(i, k)] = v
            idx += 4
        elif typ == "s":
            j, k, v = int(tokens[idx+1]), int(tokens[idx+2]), int(tokens[idx+3])
            s[(j, k)] = v
            idx += 4
        else:
            idx += 1

    return I, J, K, r, s


def validate_data(I, J, K, r, s) -> List[str]:
    """Return list of validation warnings."""
    warnings = []
    for k in K:
        supply = sum(r[(i, k)] for i in I)
        demand = sum(s[(j, k)] for j in J)
        if supply != demand:
            warnings.append(
                f"Producto {k}: oferta={supply} ≠ demanda={demand} (diferencia {supply-demand})"
            )
    return warnings


# ─────────────────────────────────────────────
#  MIP MODEL
# ─────────────────────────────────────────────

def solve_crossdock(
    I: List[int],
    J: List[int],
    K: List[int],
    r: Dict,
    s: Dict,
    M: float = 50_000,
    time_limit: int = 300,
    gap_rel: float = 0.01,
    verbose: bool = False,
) -> Dict:
    """
    Build and solve the Cross-Docking MIP.

    Decision variables
    ------------------
    Continuous : Ai, Bi, Cj, Dj, T
    Binary     : Uii', Vjj', Zij
    Integer    : Xijk

    Constraints (13)
    ----------------
    1.  T ≥ Dj
    2.  Σj Xijk = r[i,k]
    3.  Σi Xijk = s[j,k]
    4.  Xijk ≤ M·Zij
    5.  Bi = Ai + Σk r[i,k]
    6.  Ai' ≥ Bi + 10 − M(1−Uii')
    7.  Ai  ≥ Bi'+ 10 − M·Uii'
    8.  Uii = 0  (not created)
    9.  Dj = Cj + Σk s[j,k]
    10. Cj' ≥ Dj + 10 − M(1−Vjj')
    11. Cj  ≥ Dj'+ 10 − M·Vjj'
    12. Vjj = 0  (not created)
    13. Cj  ≥ Bi + 5  − M(1−Zij)
    """

    prob = pulp.LpProblem("CrossDocking_Makespan", pulp.LpMinimize)

    # ── Variables ──────────────────────────────
    A = {i: pulp.LpVariable(f"A_{i}", lowBound=0) for i in I}
    B = {i: pulp.LpVariable(f"B_{i}", lowBound=0) for i in I}
    C = {j: pulp.LpVariable(f"C_{j}", lowBound=0) for j in J}
    D = {j: pulp.LpVariable(f"D_{j}", lowBound=0) for j in J}
    T = pulp.LpVariable("T", lowBound=0)

    U = {
        (i, ip): pulp.LpVariable(f"U_{i}_{ip}", cat="Binary")
        for i in I for ip in I if i != ip
    }
    V = {
        (j, jp): pulp.LpVariable(f"V_{j}_{jp}", cat="Binary")
        for j in J for jp in J if j != jp
    }
    Z = {
        (i, j): pulp.LpVariable(f"Z_{i}_{j}", cat="Binary")
        for i in I for j in J
    }
    X = {
        (i, j, k): pulp.LpVariable(f"X_{i}_{j}_{k}", lowBound=0, cat="Integer")
        for i in I for j in J for k in K
    }

    # ── Objective ──────────────────────────────
    prob += T, "Makespan"

    # ── Constraints ────────────────────────────

    # 1. Makespan definition
    for j in J:
        prob += T >= D[j], f"C1_makespan_{j}"

    # 2. Inbound flow conservation
    for i in I:
        for k in K:
            prob += (
                pulp.lpSum(X[(i, j, k)] for j in J) == r[(i, k)],
                f"C2_inbound_{i}_{k}",
            )

    # 3. Outbound flow conservation
    for j in J:
        for k in K:
            prob += (
                pulp.lpSum(X[(i, j, k)] for i in I) == s[(j, k)],
                f"C3_outbound_{j}_{k}",
            )

    # 4. Flow-transfer linking
    for i in I:
        for j in J:
            for k in K:
                if r[(i, k)] > 0 and s[(j, k)] > 0:
                    ub = min(r[(i, k)], s[(j, k)])
                    prob += X[(i, j, k)] <= ub * Z[(i, j)], f"C4_link_{i}_{j}_{k}"
                else:
                    prob += X[(i, j, k)] == 0, f"C4_zero_{i}_{j}_{k}"

    # 5. Inbound unload time
    for i in I:
        total_r = sum(r[(i, k)] for k in K)
        prob += B[i] == A[i] + total_r, f"C5_unload_{i}"

    # 6 & 7. Inbound sequencing (disjunctive)
    for i in I:
        for ip in I:
            if i != ip:
                prob += A[ip] >= B[i] + 10 - M * (1 - U[(i, ip)]), f"C6_seq_{i}_{ip}"
                prob += A[i]  >= B[ip]+ 10 - M * U[(i, ip)],       f"C7_inv_{i}_{ip}"

    # 9. Outbound load time
    for j in J:
        total_s = sum(s[(j, k)] for k in K)
        prob += D[j] == C[j] + total_s, f"C9_load_{j}"

    # 10 & 11. Outbound sequencing (disjunctive)
    for j in J:
        for jp in J:
            if j != jp:
                prob += C[jp] >= D[j] + 10 - M * (1 - V[(j, jp)]), f"C10_seq_{j}_{jp}"
                prob += C[j]  >= D[jp]+ 10 - M * V[(j, jp)],       f"C11_inv_{j}_{jp}"

    # 13. Sync inbound → outbound
    for i in I:
        for j in J:
            prob += C[j] >= B[i] + 5 - M * (1 - Z[(i, j)]), f"C13_sync_{i}_{j}"

    # ── Solve ──────────────────────────────────
    solver = pulp.PULP_CBC_CMD(
        timeLimit=time_limit,
        gapRel=gap_rel,
        msg=1 if verbose else 0,
    )
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    obj = pulp.value(T)

    def val(v):
        return pulp.value(v) or 0.0

    results = {
        "status": status,
        "objective": obj,
        "T": val(T),
        "A": {i: val(A[i]) for i in I},
        "B": {i: val(B[i]) for i in I},
        "C": {j: val(C[j]) for j in J},
        "D": {j: val(D[j]) for j in J},
        "Z": {(i, j): round(val(Z[(i, j)])) for i in I for j in J},
        "X": {
            (i, j, k): round(val(X[(i, j, k)]))
            for i in I for j in J for k in K
            if round(val(X[(i, j, k)])) > 0
        },
        "U": {(i, ip): round(val(U[(i, ip)])) for (i, ip) in U},
        "V": {(j, jp): round(val(V[(j, jp)])) for (j, jp) in V},
    }
    return results
