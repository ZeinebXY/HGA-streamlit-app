"""milp_gurobi.py - MILP exact (Gurobi) de l'ordonnancement intégré production-maintenance.
Objectifs : "makespan" (éq. 1), "weighted" (éq. 24 : alpha*sum F_i + beta*sum T_j),
            "assist"   (éq. A8 : weighted + gamma*c_ass*delta*sum s*Z, <= K setups assistés simultanés).
Adaptations au format réel des fichiers (R, P, PM, ELEG, ELEG_PM, MDS, SDS, S_PM) :
 * machine i chargée jusqu'à R[i] ; setup du 1er job = MDS ; setup avant PM = S_PM (constant) ;
 * une activité PM k est affectée à UNE machine éligible (ELEG_PM) et UNE fenêtre-jour d, <= w_d PM par jour,
   au plus 1 PM par machine (hypothèse du MILP de l'article) ;
 * setup entre deux jobs séparés par une PM = setup entre ces deux jobs (éq. 10-11, substitution directe de S_ab) ;
 * C_max ne contraint que les PM réellement choisies ; F_i >= R_i ; une seule chaîne par machine.
 * assistance : Z_iab <= X_iab sur arcs (0|job)->job ; capacité par chevauchement (lambda, mu, u) ; pas d'assistance
   sur les setups touchant une PM.
"""
import time
import gurobipy as gp
from gurobipy import GRB


def solve_milp(inst, objective="weighted", alpha=1.0, beta=1.0, K=0, delta=0.5, gamma=1.0, c_ass=1.0,
               time_limit=3600, mip_gap=0.0, threads=0, output=False, warm=None, int_feas_tol=1e-6, eps=1e-4):
    """warm : dict(seq, pm_day, assist) (ex. res['solution'] du HGA) pour amorcer Gurobi."""
    t_build = time.time()
    nM, nJ, nK, nD = inst.nM, inst.nJ, inst.nK, inst.nD
    J = range(nJ)
    day_len = (inst.windows[1][0] - inst.windows[0][0]) if nD > 1 else 24.0
    maxs = max([max(max(r) for r in inst.mds)] + [max(max(max(r) for r in m) for m in inst.sds)] + [0])
    V = (max(inst.R) + sum(max(inst.p[i][j] for i in inst.job_machines[j]) + maxs for j in J)
         + sum(max(inst.pm[i][k] + inst.spm[i][k] for i in inst.pm_machines[k]) for k in range(nK)) + nD * day_len)
    Vi = []                                               # grand-M propre à chaque machine (plus serré)
    for i in range(nM):
        mi = max([max(inst.mds[i])] + [max(r) for r in inst.sds[i]] + [0])
        Vi.append(inst.R[i] + sum(inst.p[i][j] + mi for j in J if i in inst.job_machines[j])
                  + sum(inst.pm[i][k] + inst.spm[i][k] for k in range(nK) if i in inst.pm_machines[k]) + nD * day_len)
    V = min(V, max(Vi))
    pmn = lambda k, d: nJ + k * nD + d                    # id du noeud PM (k,d)
    nodes_pm = [(k, d) for k in range(nK) for d in range(nD)]
    assist_on = (objective == "assist" and K > 0)

    m = gp.Model("ordo")
    m.Params.OutputFlag = 1 if output else 0
    m.Params.TimeLimit = time_limit
    m.Params.MIPGap = mip_gap
    m.Params.IntFeasTol = int_feas_tol
    if threads:
        m.Params.Threads = threads

    # ------------------------------------------------ activités autorisées par machine
    acts = {i: [j for j in J if i in inst.job_machines[j]] + [pmn(k, d) for (k, d) in nodes_pm if i in inst.pm_machines[k]]
            for i in range(nM)}
    is_pm = lambda a: a >= nJ
    Y = {(i, a): m.addVar(vtype=GRB.BINARY, name=f"Y_{i}_{a}") for i in range(nM) for a in acts[i]}
    X = {}
    for i in range(nM):
        for b in acts[i]:
            X[i, 'S', b] = m.addVar(vtype=GRB.BINARY)
            X[i, b, 'E'] = m.addVar(vtype=GRB.BINARY)
            for a in acts[i]:
                if a != b and not (is_pm(a) and is_pm(b)):
                    X[i, a, b] = m.addVar(vtype=GRB.BINARY)
    C = {a: m.addVar(lb=0, ub=V, name=f"C_{a}") for a in list(J) + [pmn(k, d) for (k, d) in nodes_pm]}
    F = [m.addVar(lb=inst.R[i], name=f"F_{i}") for i in range(nM)]
    T = [m.addVar(lb=0, name=f"T_{j}") for j in J]
    Cmax = m.addVar(lb=0, name="Cmax")
    ysum = {a: gp.quicksum(Y[i, a] for i in range(nM) if (i, a) in Y) for a in C}

    # ------------------------------------------------ affectation / chaîne
    for j in J:
        m.addConstr(ysum[j] == 1)
    for k in range(nK):
        m.addConstr(gp.quicksum(ysum[pmn(k, d)] for d in range(nD)) == 1)
    for d in range(nD):
        m.addConstr(gp.quicksum(ysum[pmn(k, d)] for k in range(nK)) <= inst.w[d])
    for i in range(nM):
        pms = [a for a in acts[i] if is_pm(a)]
        if pms:
            m.addConstr(gp.quicksum(Y[i, a] for a in pms) <= 1)
        for b in acts[i]:
            m.addConstr(gp.quicksum(X[i, a, b] for a in ['S'] + acts[i] if (i, a, b) in X) == Y[i, b])
            m.addConstr(gp.quicksum(X[i, b, c] for c in acts[i] + ['E'] if (i, b, c) in X) == Y[i, b])
            m.addConstr(gp.quicksum(X[i, 'S', c] for c in acts[i]) >= Y[i, b])
            m.addConstr(gp.quicksum(X[i, c, 'E'] for c in acts[i]) >= Y[i, b])
        m.addConstr(gp.quicksum(X[i, 'S', c] for c in acts[i]) <= 1)
        m.addConstr(gp.quicksum(X[i, c, 'E'] for c in acts[i]) <= 1)

    # ------------------------------------------------ assistance : variables
    Z = {}
    if assist_on:
        for i in range(nM):
            for b in acts[i]:
                if is_pm(b):
                    continue
                for a in ['S'] + [x for x in acts[i] if not is_pm(x) and x != b]:
                    s = inst.mds[i][b] if a == 'S' else inst.sds[i][a][b]
                    if s > 1e-9:
                        Z[i, a, b] = m.addVar(vtype=GRB.BINARY)
                        m.addConstr(Z[i, a, b] <= X[i, a, b])

    def setup_expr(i, a, b):                     # setup effectif a->b (jobs ou début)
        s = inst.mds[i][b] if a == 'S' else inst.sds[i][a][b]
        if (i, a, b) in Z:
            return s * (1 - delta * Z[i, a, b])
        return s

    # ------------------------------------------------ contraintes temporelles
    for (i, a, b), xv in X.items():
        if b == 'E':
            continue
        start = inst.R[i] if a == 'S' else C[a]
        if not is_pm(b):                                           # -> job b
            if a == 'S' or not is_pm(a):
                m.addConstr(C[b] >= start + setup_expr(i, a, b) + inst.p[i][b] - Vi[i] * (1 - xv))
            else:                                                  # PM -> job : setup du job d'avant la PM
                prev = ['S'] + [x for x in acts[i] if not is_pm(x) and x != b]
                m.addConstr(C[b] >= C[a] + inst.p[i][b] - Vi[i] * (1 - xv) + gp.quicksum(
                    X[i, x, a] * (inst.mds[i][b] if x == 'S' else inst.sds[i][x][b]) for x in prev if (i, x, a) in X))
        else:                                                      # -> PM (k,d)
            k = (b - nJ) // nD
            m.addConstr(C[b] >= start + inst.spm[i][k] + inst.pm[i][k] - Vi[i] * (1 - xv))
    for (k, d) in nodes_pm:                                        # fenêtre de la PM
        a = pmn(k, d); rel, due = inst.windows[d]
        m.addConstr(C[a] >= rel + gp.quicksum(inst.pm[i][k] * Y[i, a] for i in inst.pm_machines[k]))
        m.addConstr(C[a] <= due + max(0.0, V - due) * (1 - ysum[a]))

    # ------------------------------------------------ coupe de charge (valide, resserre la relaxation)
    def saved(i):      # gain de temps dû à l'assistance sur la machine i (0 si pas d'assistance)
        zs = [(a, b, z) for (ii, a, b), z in Z.items() if ii == i]
        return delta * gp.quicksum((inst.mds[i][b] if a == 'S' else inst.sds[i][a][b]) * z for a, b, z in zs)

    load = {}
    for i in range(nM):
        e = inst.R[i] + gp.quicksum(inst.p[i][a] * Y[i, a] for a in acts[i] if not is_pm(a))
        e = e + gp.quicksum(inst.pm[i][(a - nJ) // nD] * Y[i, a] for a in acts[i] if is_pm(a))
        for (ii, a, b), xv in X.items():
            if ii != i or b == 'E':
                continue
            if is_pm(b):
                e = e + inst.spm[i][(b - nJ) // nD] * xv
            elif a == 'S':
                e = e + inst.mds[i][b] * xv
            elif not is_pm(a):
                e = e + inst.sds[i][a][b] * xv
        load[i] = e - saved(i)
    # ------------------------------------------------ objectifs
    if objective == "makespan":
        for j in J:
            m.addConstr(Cmax >= C[j])
        for (k, d) in nodes_pm:
            m.addConstr(Cmax >= C[pmn(k, d)] - V * (1 - ysum[pmn(k, d)]))
        for i in range(nM):
            m.addConstr(Cmax >= load[i])
        m.setObjective(Cmax, GRB.MINIMIZE)
    else:
        for j in J:
            m.addConstr(T[j] >= C[j] - inst.due[j])
        for (i, a, e), xv in X.items():
            if e == 'E':
                m.addConstr(F[i] >= C[a] - Vi[i] * (1 - xv))
        for i in range(nM):
            m.addConstr(F[i] >= load[i])
        obj = alpha * gp.quicksum(F) + beta * gp.quicksum(T)
        if assist_on:
            obj = obj + gamma * c_ass * delta * gp.quicksum(
                (inst.mds[i][b] if a == 'S' else inst.sds[i][a][b]) * z for (i, a, b), z in Z.items())
        m.setObjective(obj, GRB.MINIMIZE)

    # ------------------------------------------------ capacité des assistants (chevauchement)
    if assist_on:
        Q = {b: gp.quicksum(z for (i, a, bb), z in Z.items() if bb == b) for b in J}
        sig = {b: m.addVar(lb=-V, ub=V) for b in J}
        St = {b: C[b] - gp.quicksum(inst.p[i][b] * Y[i, b] for i in inst.job_machines[b]) for b in J}
        for b in J:
            m.addConstr(sig[b] == St[b] - gp.quicksum(
                (inst.mds[i][b] if a == 'S' else inst.sds[i][a][b]) * (X[i, a, bb] - delta * Z[i, a, bb])
                for (i, a, bb) in Z if bb == b))
        lam, mu, u = {}, {}, {}
        for b in J:
            for b2 in J:
                if b2 == b:
                    continue
                lam[b2, b], mu[b2, b], u[b2, b] = (m.addVar(vtype=GRB.BINARY) for _ in range(3))
                m.addConstr(sig[b2] >= sig[b] + eps - V * lam[b2, b])      # sigma_b' <= sigma_b  => lam=1
                m.addConstr(sig[b] >= St[b2] - V * mu[b2, b])              # sigma_b < fin traitement b' => mu=1
                m.addConstr(u[b2, b] >= lam[b2, b] + mu[b2, b] + Q[b2] + Q[b] - 3)
            m.addConstr(gp.quicksum(u[b2, b] for b2 in J if b2 != b) <= (K - 1) + (nJ - 1) * (1 - Q[b]))

    # ------------------------------------------------ warm start
    if warm:
        pdy = warm["pm_day"]
        for (i, a), yv in Y.items():
            yv.Start = 0
        for xv in X.values():
            xv.Start = 0
        for zv in Z.values():
            zv.Start = 0
        asg = set(warm.get("assist", []))
        for i, q in enumerate(warm["seq"]):
            chain = ['S'] + [(a if a < nJ else pmn(a - nJ, pdy[a - nJ])) for a in q] + ['E']
            for a in chain[1:-1]:
                if (i, a) in Y:
                    Y[i, a].Start = 1
            for a, b in zip(chain[:-1], chain[1:]):
                if (i, a, b) in X:
                    X[i, a, b].Start = 1
                    if (i, a, b) in Z and b in asg:
                        Z[i, a, b].Start = 1

    # ------------------------------------------------ résolution + suivi de l'incumbent
    state = {"best": None, "t_best": None}

    def cb(model, where):
        if where == GRB.Callback.MIP:
            ob = model.cbGet(GRB.Callback.MIP_OBJBST)
            if ob < 1e99 and (state["best"] is None or ob < state["best"] - 1e-9):
                state["best"], state["t_best"] = ob, model.cbGet(GRB.Callback.RUNTIME)

    t0 = time.time()
    m.optimize(cb)
    runtime = time.time() - t0
    res = dict(status=m.Status, status_name={2: "OPTIMAL", 9: "TIME_LIMIT", 3: "INFEASIBLE"}.get(m.Status, str(m.Status)),
               runtime=runtime, build_time=t0 - t_build, nvars=m.NumVars, nbin=m.NumBinVars, nconstr=m.NumConstrs,
               time_to_best=state["t_best"], obj=None, bound=None, gap=None, proven_optimal=(m.Status == GRB.OPTIMAL), solution=None)
    if m.SolCount > 0:
        res.update(obj=m.ObjVal, bound=m.ObjBound, gap=100 * m.MIPGap)
        seq, pm_day = [], {}
        for i in range(nM):
            q, cur = [], 'S'
            while True:
                nxt = next((c for c in acts[i] + ['E'] if (i, cur, c) in X and X[i, cur, c].X > 0.5), 'E')
                if nxt == 'E':
                    break
                if is_pm(nxt):
                    k, d = (nxt - nJ) // nD, (nxt - nJ) % nD
                    pm_day[k] = d; q.append(nJ + k)
                else:
                    q.append(nxt)
                cur = nxt
            seq.append(q)
        res["solution"] = dict(seq=seq, pm_day=pm_day,
                               assist=sorted({b for (i, a, b), z in Z.items() if z.X > 0.5}))
    return res
