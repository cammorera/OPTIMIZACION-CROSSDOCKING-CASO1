"""
Cross-Docking MIP Solver — LogiFast CR
Solves sequencing + flow optimization via full enumeration (feasible for small instances)
and a greedy heuristic for larger ones.
"""
import re
import math
from itertools import permutations
from typing import Dict, Tuple, List, Optional
 
# ─── Operational Parameters ───────────────────────────────────────────────────
T_LOAD      = 1   # minutes per unit (load or unload)
T_TRANSFER  = 5   # minutes per lot (internal move)
T_CHANGE    = 10  # minutes between trucks at dock
 
 
# ─── Data Parsing ─────────────────────────────────────────────────────────────
 
def parse_ts_file(content: str) -> dict:
    """
    Parse TS5-format text.  Returns:
        {'I': int, 'O': int, 'N': int,
         'supply': {(i,k): qty}, 'demand': {(j,k): qty}}
    """
    tokens = re.split(r'\s+', content.strip())
 
    def _get(label):
        idx = tokens.index(label)
        return int(tokens[idx + 1])
 
    I = _get('i')
    O = _get('o')
    N = _get('n')
 
    # Re-join and extract r / s entries robustly
    flat = ''.join(tokens)
    r_entries = re.findall(r'r(\d+)\s*(\d+)\s*(\d+)', ' '.join(tokens))
    s_entries = re.findall(r's(\d+)\s*(\d+)\s*(\d+)', ' '.join(tokens))
 
    # fallback with flat string
    if not r_entries:
        r_entries = re.findall(r'r(\d+)(\d+)(\d+)', flat)
        s_entries = re.findall(r's(\d+)(\d+)(\d+)', flat)
 
    supply = {}
    for truck, prod, qty in r_entries:
        supply[(int(truck), int(prod))] = int(qty)
 
    demand = {}
    for truck, prod, qty in s_entries:
        demand[(int(truck), int(prod))] = int(qty)
 
    return {'I': I, 'O': O, 'N': N, 'supply': supply, 'demand': demand}
 
 
# ─── Product Flow Assignment ───────────────────────────────────────────────────
 
def solve_product_flow(I_list, J_list, K_list, supply, demand) -> Dict:
    """
    Solve the transportation sub-problem for each product k independently.
    Returns x[(i,j,k)] = units of product k from inbound i to outbound j.
    Uses a greedy northwest-corner method (optimal for flow feasibility).
    """
    x = {(i, j, k): 0 for i in I_list for j in J_list for k in K_list}
 
    for k in K_list:
        rem_s = {i: supply.get((i, k), 0) for i in I_list}
        rem_d = {j: demand.get((j, k), 0) for j in J_list}
        for i in I_list:
            for j in J_list:
                t = min(rem_s[i], rem_d[j])
                if t > 0:
                    x[(i, j, k)] = t
                    rem_s[i] -= t
                    rem_d[j] -= t
 
    return x
 
 
# ─── Makespan Computation ──────────────────────────────────────────────────────
 
def compute_makespan(perm_i, perm_j, U, D, x, I_list, J_list, K_list):
    """
    Given ordered sequences for inbound/outbound docks, compute makespan.
 
    Inbound dock (sequential):
        a[perm_i[0]] = 0
        a[perm_i[p]] = a[perm_i[p-1]] + U[perm_i[p-1]] + T_CHANGE
 
    Outbound dock (sequential):
        Each outbound truck j waits until:
          - All its products have been transferred from their inbound trucks
          - The outbound dock is free
        d[j] = start_load[j] + D[j]
    """
    # Inbound arrival at dock
    a = {}
    t = 0
    for i in perm_i:
        a[i] = t
        t += U[i] + T_CHANGE
 
    # Outbound departure
    d = {}
    out_dock_free = 0
    for j in perm_j:
        # Earliest all units for j are available (after inbound unloads + internal transfer)
        earliest_ready = 0
        for i in I_list:
            units_ij = sum(x.get((i, j, k), 0) for k in K_list)
            if units_ij > 0:
                ready = a[i] + U[i] + T_TRANSFER
                earliest_ready = max(earliest_ready, ready)
 
        start_load = max(earliest_ready, out_dock_free)
        d[j] = start_load + D[j]
        out_dock_free = d[j] + T_CHANGE
 
    makespan = max(d.values()) if d else 0
    return makespan, a, d
 
 
# ─── Full Enumeration Solver ───────────────────────────────────────────────────
 
def enumerate_best(data: dict):
    """
    Enumerate all (I! × O!) sequences and return the optimal schedule.
    Feasible up to ~I=7, O=5.
    """
    I_list = list(range(1, data['I'] + 1))
    J_list = list(range(1, data['O'] + 1))
    K_list = list(range(1, data['N'] + 1))
    supply = data['supply']
    demand = data['demand']
 
    U = {i: sum(supply.get((i, k), 0) for k in K_list) for i in I_list}
    D = {j: sum(demand.get((j, k), 0) for k in K_list) for j in J_list}
 
    x = solve_product_flow(I_list, J_list, K_list, supply, demand)
 
    best_ms = float('inf')
    best_pi = None
    best_pj = None
    all_results = []
 
    n_combos = math.factorial(len(I_list)) * math.factorial(len(J_list))
 
    for pi in permutations(I_list):
        for pj in permutations(J_list):
            ms, a, d = compute_makespan(pi, pj, U, D, x, I_list, J_list, K_list)
            all_results.append((ms, pi, pj))
            if ms < best_ms:
                best_ms = ms
                best_pi = pi
                best_pj = pj
 
    best_ms, a, d = compute_makespan(best_pi, best_pj, U, D, x, I_list, J_list, K_list)
 
    return {
        'makespan': best_ms,
        'inbound_order': best_pi,
        'outbound_order': best_pj,
        'a': a,
        'd': d,
        'U': U,
        'D': D,
        'x': x,
        'I_list': I_list,
        'J_list': J_list,
        'K_list': K_list,
        'supply': supply,
        'demand': demand,
        'n_combos': n_combos,
        'all_results': sorted(all_results)[:20],  # top 20
    }
 
 
# ─── Greedy Heuristic (for large instances) ───────────────────────────────────
 
def greedy_solve(data: dict):
    """
    Greedy heuristic: sort inbound by total units ASC (earliest completion),
    sort outbound by earliest product availability.
    """
    I_list = list(range(1, data['I'] + 1))
    J_list = list(range(1, data['O'] + 1))
    K_list = list(range(1, data['N'] + 1))
    supply = data['supply']
    demand = data['demand']
 
    U = {i: sum(supply.get((i, k), 0) for k in K_list) for i in I_list}
    D = {j: sum(demand.get((j, k), 0) for k in K_list) for j in J_list}
 
    x = solve_product_flow(I_list, J_list, K_list, supply, demand)
 
    # Sort inbound by size ASC (shorter trucks first to release products faster)
    pi = tuple(sorted(I_list, key=lambda i: U[i]))
    pj = tuple(sorted(J_list, key=lambda j: D[j]))
 
    ms, a, d = compute_makespan(pi, pj, U, D, x, I_list, J_list, K_list)
 
    return {
        'makespan': ms,
        'inbound_order': pi,
        'outbound_order': pj,
        'a': a,
        'd': d,
        'U': U,
        'D': D,
        'x': x,
        'I_list': I_list,
        'J_list': J_list,
        'K_list': K_list,
        'supply': supply,
        'demand': demand,
        'n_combos': 1,
        'all_results': [(ms, pi, pj)],
    }
 
 
# ─── Auto-select solver ───────────────────────────────────────────────────────
 
MAX_ENUM = 40320  # 8! — beyond this use greedy
 
def solve(data: dict):
    n_combos = math.factorial(data['I']) * math.factorial(data['O'])
    if n_combos <= MAX_ENUM:
        return enumerate_best(data)
    else:
        return greedy_solve(data)
 
 
# ─── Transfer summary ─────────────────────────────────────────────────────────
 
def build_transfer_table(result: dict) -> List[dict]:
    rows = []
    x = result['x']
    supply = result['supply']
    demand = result['demand']
    for i in result['I_list']:
        for j in result['J_list']:
            total_ij = sum(x.get((i, j, k), 0) for k in result['K_list'])
            if total_ij > 0:
                products = {k: x.get((i, j, k), 0) for k in result['K_list']
                            if x.get((i, j, k), 0) > 0}
                rows.append({
                    'Camión Entrada': f"R{i}",
                    'Camión Salida': f"S{j}",
                    'Total Unidades': total_ij,
                    'Productos': ', '.join(f"P{k}:{v}" for k, v in products.items()),
                })
    return rows
 
 
def storage_analysis(result: dict) -> dict:
    """
    Determine which transfers go directly vs. through temp storage.
    A transfer from i to j is 'direct' if inbound i finishes before outbound j starts loading.
    """
    a = result['a']
    d = result['d']
    U = result['U']
    x = result['x']
    J_list = result['J_list']
    K_list = result['K_list']
 
    # Compute outbound start times
    out_dock_free = 0
    start_load = {}
    for j in result['outbound_order']:
        earliest_ready = 0
        for i in result['I_list']:
            units_ij = sum(x.get((i, j, k), 0) for k in K_list)
            if units_ij > 0:
                ready = a[i] + U[i] + T_TRANSFER
                earliest_ready = max(earliest_ready, ready)
        sl = max(earliest_ready, out_dock_free)
        start_load[j] = sl
        out_dock_free = sl + result['D'][j] + T_CHANGE
 
    direct = 0
    storage = 0
    storage_lots = []
 
    for i in result['I_list']:
        inbound_done = a[i] + U[i]
        for j in J_list:
            units_ij = sum(x.get((i, j, k), 0) for k in K_list)
            if units_ij > 0:
                if inbound_done + T_TRANSFER <= start_load[j]:
                    direct += units_ij
                else:
                    storage += units_ij
                    wait = start_load[j] - (inbound_done + T_TRANSFER)
                    storage_lots.append({
                        'De': f"R{i}", 'Para': f"S{j}",
                        'Unidades': units_ij,
                        'Espera (min)': max(0, wait)
                    })
 
    total = direct + storage
    return {
        'direct': direct,
        'storage': storage,
        'pct_direct': round(100 * direct / total, 1) if total else 0,
        'start_load': start_load,
        'storage_lots': storage_lots,
    }
