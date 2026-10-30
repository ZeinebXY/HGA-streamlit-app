"""hga.py - Algorithme génétique hybride (HGA) pour l'ordonnancement intégré production-maintenance.
3 objectifs :  makespan | weighted (alpha*TMCT + beta*TT) | assist (weighted + gamma*c_ass*delta*sum(s*Z), <=K assistants)
Représentation (article, §5.1) : seq[i] = liste d'activités de la machine i (jobs 0..J-1, PM k = J+k)
 + pm_day[k] = jour/fenêtre de la PM k (la 'liste de réclamations de ressource') + assist[j] (setup assisté).
Évaluation incrémentale : un changement ne ré-évalue que les machines touchées.
Boucle steady-state : sélection aléatoire, croisement, r mutations, recherche locale, remplacement du pire si unique et meilleur.
"""
import math, random, time
from dataclasses import dataclass

BIG = 1e6


@dataclass
class HGAParams:
    objective: str = "weighted"      # makespan | weighted | assist
    alpha: float = 1.0               # poids TMCT
    beta: float = 1.0                # poids retard total
    K: int = 0                       # nb d'assistants simultanés (assist)
    delta: float = 0.5               # taux de réduction du setup assisté
    gamma: float = 1.0               # poids du coût d'assistance
    c_ass: float = 1.0               # coût unitaire d'assistance
    pop: int = 10                    # taille de population P
    gmax: int = 2000                 # nb de générations (= enfants produits)
    n_mut: int = 1                   # r : nb de mutations par enfant
    pc: float = 1.0                  # probabilité de croisement
    pm: float = 1.0                  # probabilité de muter un enfant
    p_ls: float = 1.0                # probabilité d'appliquer la recherche locale
    n_ls: int = 50                   # nb max d'itérations de LS (jusqu'à minimum local)
    d_ins: float = 1.0               # profondeur voisinage insertion (fraction des machines)
    d_swap: float = 1.0              # profondeur voisinage swap
    n_elite: int = 1                 # individus jamais remplacés
    crossover: str = "one_point"     # one_point | uniform
    mut_ops: tuple = ("worst_machine",)   # worst_machine | swap | insert | pm_day | assist_flip
    time_limit: float = None
    stagnation: int = None
    target: float = None             # arrêt si obj <= target


class Sol:
    __slots__ = ("seq", "pm_day", "assist", "mv", "fit", "obj", "feasible")

    def copy(self):
        s = Sol()
        s.seq = [q[:] for q in self.seq]
        s.pm_day = self.pm_day[:]
        s.assist = self.assist[:] if self.assist is not None else None
        s.mv, s.fit, s.obj, s.feasible = self.mv, self.fit, self.obj, self.feasible
        return s

    def key(self):
        return (tuple(tuple(q) for q in self.seq), tuple(self.pm_day),
                tuple(self.assist) if self.assist is not None else None)


class Engine:
    def __init__(self, inst, P, seed=0):
        self.inst, self.P, self.rng = inst, P, random.Random(seed)
        self.nM, self.nJ, self.nK, self.nD = inst.nM, inst.nJ, inst.nK, inst.nD
        self.assist_on = (P.objective == "assist" and P.K > 0)
        self.nev = 0

    # ---------------------------------------------------------------- évaluation d'une machine
    def meval(self, i, seq, pm_day, assist):
        inst, P = self.inst, self.P
        self.nev += 1
        t = inst.R[i]; prev = -1; after_pm = False
        T = pen = ac = 0.0; ints = []
        nJ = self.nJ
        for a in seq:
            if a < nJ:
                s = inst.mds[i][a] if prev < 0 else inst.sds[i][prev][a]
                if assist is not None and assist[a] and not after_pm and s > 0:
                    ints.append((t, t + s * (1 - P.delta), a))
                    ac += P.gamma * P.c_ass * P.delta * s
                    s *= (1 - P.delta)
                t += s + inst.p[i][a]
                if t > inst.due[a]:
                    T += t - inst.due[a]
                prev = a; after_pm = False
            else:
                k = a - nJ
                rel, due = inst.windows[pm_day[k]]
                t = max(t + inst.spm[i][k], rel) + inst.pm[i][k]
                if t > due + 1e-9:
                    pen += BIG * (1 + t - due)
                after_pm = True
        return (t if seq else inst.R[i], T, pen, ac, ints, bool(seq))

    def cap_violation(self, ints):
        K = self.P.K
        if not ints:
            return None
        for (s, e, a) in ints:
            act = [x for x in ints if x[0] <= s + 1e-9 and s < x[1] - 1e-9]
            if len(act) > K:
                return min(act, key=lambda x: x[1] - x[0])[2]
        return None

    def full(self, seq, pm_day, assist):
        if self.P.objective != "assist":
            assist = None
        elif assist is not None:
            assist = assist[:]
            if self.P.K == 0:
                assist = [False] * self.nJ
        while True:
            mvs = [self.meval(i, seq[i], pm_day, assist) for i in range(self.nM)]
            if not self.assist_on:
                return mvs, assist
            v = self.cap_violation([x for mv in mvs for x in mv[4]])
            if v is None:
                return mvs, assist
            assist[v] = False

    def score(self, mvs):
        """-> (fitness, objectif réel, faisable)"""
        P = self.P
        sF = sT = sp = sa = 0.0; mx = 0.0
        for (F, T, pen, ac, _, ne) in mvs:
            sF += F; sT += T; sp += pen; sa += ac
            if ne and F > mx:
                mx = F
        if P.objective == "makespan":
            return mx + 1e-4 * sF + sp, mx + sp, sp == 0
        o = P.alpha * sF + P.beta * sT + (sa if P.objective == "assist" else 0.0) + sp
        return o, o, sp == 0

    def evaluate(self, sol):
        sol.mv, asg = self.full(sol.seq, sol.pm_day, sol.assist)
        if asg is not None:
            sol.assist = asg
        sol.fit, sol.obj, sol.feasible = self.score(sol.mv)
        return sol

    def fit_with(self, sol, changes, pm_day=None, assist=None):
        """fitness du voisin : changes={machine:nouvelle_seq}. -> (fit, mvs, assist)"""
        pdy = pm_day if pm_day is not None else sol.pm_day
        asg = assist if assist is not None else sol.assist
        if self.assist_on:
            seq = list(sol.seq)
            for i, q in changes.items():
                seq[i] = q
            mvs, asg = self.full(seq, pdy, asg)
        else:
            mvs = list(sol.mv)
            for i, q in changes.items():
                mvs[i] = self.meval(i, q, pdy, None)
        return self.score(mvs)[0], mvs, asg

    def apply(self, sol, changes, mvs, asg, pm_day=None):
        for i, q in changes.items():
            sol.seq[i] = q
        if pm_day is not None:
            sol.pm_day = pm_day
        if self.P.objective == "assist":
            sol.assist = asg
        sol.mv = mvs
        sol.fit, sol.obj, sol.feasible = self.score(mvs)

    # ---------------------------------------------------------------- utilitaires
    def day_load(self, sol_days, placed_pm, excl=None):
        load = [0] * self.nD
        for k in placed_pm:
            if k != excl and sol_days[k] >= 0:
                load[sol_days[k]] += 1
        return load

    def placed_pms(self, sol):
        return {a - self.nJ: i for i in range(self.nM) for a in sol.seq[i] if a >= self.nJ}

    def free_days(self, sol, k, placed):
        load = self.day_load(sol.pm_day, placed, excl=k)
        return [d for d in range(self.nD) if load[d] < self.inst.w[d]]

    def allowed_machines(self, sol, a, placed_machines):
        if a < self.nJ:
            return self.inst.job_machines[a]
        return [i for i in self.inst.pm_machines[a - self.nJ] if i not in placed_machines]

    def best_insert(self, sol, a, machines=None, force_other=None):
        """insère l'activité a (déjà retirée) à la meilleure position ; PM : teste aussi les jours libres."""
        placed = self.placed_pms(sol)
        pm_hold = set(placed.values())
        cands = machines if machines is not None else self.allowed_machines(sol, a, pm_hold)
        best = None
        if a < self.nJ:
            day_opts = [None]
        else:
            day_opts = self.free_days(sol, a - self.nJ, placed) or list(range(self.nD))
        for i in cands:
            base = sol.seq[i]
            for pos in range(len(base) + 1):
                new = base[:pos] + [a] + base[pos:]
                for d in day_opts:
                    pdy = sol.pm_day
                    if d is not None:
                        pdy = sol.pm_day[:]; pdy[a - self.nJ] = d
                    f, mvs, asg = self.fit_with(sol, {i: new}, pm_day=pdy)
                    if best is None or f < best[0]:
                        best = (f, i, new, mvs, asg, pdy if d is not None else None)
        _, i, new, mvs, asg, pdy = best
        self.apply(sol, {i: new}, mvs, asg, pm_day=pdy)

    def repair_days(self, sol):
        placed = self.placed_pms(sol)
        load = [0] * self.nD
        for k in sorted(placed):
            d = sol.pm_day[k]
            if d < 0 or load[d] >= self.inst.w[d]:
                free = [x for x in range(self.nD) if load[x] < self.inst.w[x]]
                d = min(free, key=lambda x: abs(x - max(d, 0))) if free else max(d, 0)
                sol.pm_day[k] = d
            load[d] += 1

    # ---------------------------------------------------------------- initialisation
    def init_solution(self):
        nJ, nK = self.nJ, self.nK
        s = Sol()
        s.seq = [[] for _ in range(self.nM)]
        s.pm_day = [-1] * nK
        s.assist = [False] * nJ if self.P.objective == "assist" else None
        self.evaluate(s)
        acts = list(range(nJ + nK))
        self.rng.shuffle(acts)
        for a in acts:                      # Fisher-Yates + meilleure insertion
            self.best_insert(s, a)
        if self.assist_on:                  # assistance aléatoire pour diversifier
            for j in range(nJ):
                s.assist[j] = self.rng.random() < 0.5
        return self.evaluate(s)

    # ---------------------------------------------------------------- croisement
    def crossover(self, A, B):
        M = self.nM
        cut = self.rng.randint(1, max(1, M - 1))
        kids = []
        for (X, Y) in ((A, B), (B, A)):
            if self.P.crossover == "uniform":
                src = [X if self.rng.random() < 0.5 else Y for _ in range(M)]
            else:
                src = [X if i < cut else Y for i in range(M)]
            c = Sol()
            c.seq, seen, c.pm_day = [], set(), [-1] * self.nK
            for i in range(M):
                q = []
                for a in src[i].seq[i]:
                    if a in seen:
                        continue
                    seen.add(a); q.append(a)
                    if a >= self.nJ:
                        c.pm_day[a - self.nJ] = src[i].pm_day[a - self.nJ]
                c.seq.append(q)
            c.assist = None
            if self.P.objective == "assist":
                c.assist = [(src[0].assist[j] if self.rng.random() < .5 else src[-1].assist[j]) for j in range(self.nJ)]
            self.repair_days(c)
            self.evaluate(c)
            miss = [a for a in range(self.nJ + self.nK) if a not in seen]
            self.rng.shuffle(miss)
            for a in miss:
                self.best_insert(c, a)
            self.evaluate(c)
            kids.append(c)
        return kids

    # ---------------------------------------------------------------- mutations
    def mutate(self, sol):
        for _ in range(self.P.n_mut):
            op = self.rng.choice(self.P.mut_ops)
            if op == "assist_flip" and not self.assist_on:
                op = "swap"
            getattr(self, "_mut_" + op)(sol)
        return self.evaluate(sol)

    def _mut_worst_machine(self, sol):
        ne = [i for i in range(self.nM) if sol.seq[i]]
        w = max(ne, key=lambda i: sol.mv[i][0])
        removed = sol.seq[w]
        sol.seq[w] = []
        self.evaluate(sol)
        for a in removed:
            held = {m for m in range(self.nM) if any(x >= self.nJ for x in sol.seq[m])}
            c = self.allowed_machines(sol, a, held)
            others = [m for m in c if m != w] or c
            self.best_insert(sol, a, machines=[self.rng.choice(others)])

    def _mut_swap(self, sol):
        pos = [(i, n) for i in range(self.nM) for n, a in enumerate(sol.seq[i]) if a < self.nJ]
        if len(pos) < 2:
            return
        for _ in range(10):
            (i, n), (j, m) = self.rng.sample(pos, 2)
            a, b = sol.seq[i][n], sol.seq[j][m]
            if i != j and (j not in self.inst.job_machines[a] or i not in self.inst.job_machines[b]):
                continue
            if i == j:
                sol.seq[i][n], sol.seq[i][m] = b, a
            else:
                sol.seq[i][n], sol.seq[j][m] = b, a
            return

    def _mut_insert(self, sol):
        pos = [(i, a) for i in range(self.nM) for a in sol.seq[i] if a < self.nJ]
        i, a = self.rng.choice(pos)
        sol.seq[i].remove(a)
        j = self.rng.choice(self.inst.job_machines[a])
        sol.seq[j].insert(self.rng.randint(0, len(sol.seq[j])), a)

    def _mut_pm_day(self, sol):
        if not self.nK:
            return
        k = self.rng.randrange(self.nK)
        placed = self.placed_pms(sol)
        fd = self.free_days(sol, k, placed)
        if fd:
            sol.pm_day[k] = self.rng.choice(fd)
        elif self.nK > 1:
            k2 = self.rng.choice([x for x in range(self.nK) if x != k])
            sol.pm_day[k], sol.pm_day[k2] = sol.pm_day[k2], sol.pm_day[k]

    def _mut_assist_flip(self, sol):
        j = self.rng.randrange(self.nJ)
        sol.assist[j] = not sol.assist[j]

    # ---------------------------------------------------------------- recherche locale
    def ls_insert(self, sol):
        M, improved = self.nM, False
        order = sorted(range(M), key=lambda i: -sol.mv[i][0])[:max(1, math.ceil(self.P.d_ins * M))]
        for i in order:
            if not sol.seq[i]:
                continue
            best = (sol.fit - 1e-9, None)
            held = {m for m in range(M) if any(x >= self.nJ for x in sol.seq[m])}
            for a in list(sol.seq[i]):
                rem = [x for x in sol.seq[i] if x != a]
                if a < self.nJ:
                    cand = self.inst.job_machines[a]
                else:
                    cand = [m for m in self.inst.pm_machines[a - self.nJ] if m == i or m not in held]
                for j in cand:
                    base = rem if j == i else sol.seq[j]
                    for pos in range(len(base) + 1):
                        new = base[:pos] + [a] + base[pos:]
                        if j == i and new == sol.seq[i]:
                            continue
                        ch = {i: new} if j == i else {i: rem, j: new}
                        f, mvs, asg = self.fit_with(sol, ch)
                        if f < best[0]:
                            best = (f, (ch, mvs, asg))
            if best[1]:
                self.apply(sol, *best[1]); improved = True
        return improved

    def ls_swap(self, sol):
        M, improved = self.nM, False
        order = sorted(range(M), key=lambda i: -sol.mv[i][0])[:max(1, math.ceil(self.P.d_swap * M))]
        jm = self.inst.job_machines
        for i in order:
            best = (sol.fit - 1e-9, None)
            for n, a in enumerate(sol.seq[i]):
                if a >= self.nJ:
                    continue
                for j in range(M):
                    for m, b in enumerate(sol.seq[j]):
                        if b >= self.nJ or b == a or (j == i and m <= n):
                            continue
                        if j != i and (j not in jm[a] or i not in jm[b]):
                            continue
                        if j == i:
                            q = sol.seq[i][:]; q[n], q[m] = b, a; ch = {i: q}
                        else:
                            qi = sol.seq[i][:]; qi[n] = b
                            qj = sol.seq[j][:]; qj[m] = a; ch = {i: qi, j: qj}
                        f, mvs, asg = self.fit_with(sol, ch)
                        if f < best[0]:
                            best = (f, (ch, mvs, asg))
            if best[1]:
                self.apply(sol, *best[1]); improved = True
        return improved

    def ls_pm_day(self, sol):
        improved = False
        for k in range(self.nK):
            placed = self.placed_pms(sol)
            if k not in placed:
                continue
            i = placed[k]
            load = self.day_load(sol.pm_day, placed)
            best = (sol.fit - 1e-9, None)
            for d in range(self.nD):
                if d == sol.pm_day[k]:
                    continue
                pdy = sol.pm_day[:]; pdy[k] = d; ch = {i: sol.seq[i]}
                if load[d] >= self.inst.w[d]:       # échange avec une PM déjà sur ce jour
                    k2 = next((x for x in placed if sol.pm_day[x] == d), None)
                    if k2 is None:
                        continue
                    pdy[k2] = sol.pm_day[k]; ch[placed[k2]] = sol.seq[placed[k2]]
                f, mvs, asg = self.fit_with(sol, ch, pm_day=pdy)
                if f < best[0]:
                    best = (f, (ch, mvs, asg, pdy))
            if best[1]:
                ch, mvs, asg, pdy = best[1]
                self.apply(sol, ch, mvs, asg, pm_day=pdy); improved = True
        return improved

    def ls_assist(self, sol):
        improved = False
        for j in self.rng.sample(range(self.nJ), self.nJ):
            asg = sol.assist[:]; asg[j] = not asg[j]
            f, mvs, a2 = self.fit_with(sol, {}, assist=asg)
            if f < sol.fit - 1e-9:
                self.apply(sol, {}, mvs, a2); improved = True
        return improved

    def local_search(self, sol):
        for _ in range(self.P.n_ls):
            imp = self.ls_insert(sol)
            imp = self.ls_swap(sol) or imp
            if self.nK:
                imp = self.ls_pm_day(sol) or imp
            if self.assist_on:
                imp = self.ls_assist(sol) or imp
            if not imp:
                break
        return sol


# ---------------------------------------------------------------- API
def run_hga(inst, P, seed=0, init=None):
    """init : liste optionnelle de Sol à injecter dans la population initiale."""
    t0 = time.time()
    E = Engine(inst, P, seed)
    pop = list(init or [])
    keys = {s.key() for s in pop}
    guard = 0
    while len(pop) < P.pop and guard < 20 * P.pop:
        guard += 1
        s = E.init_solution()
        if s.key() in keys:
            continue
        keys.add(s.key()); pop.append(s)
    best = min(pop, key=lambda s: s.fit).copy()
    trace, times, last_imp = [best.obj], [time.time() - t0], 0
    g = 0
    for g in range(1, P.gmax + 1):
        if P.time_limit and time.time() - t0 >= P.time_limit:
            break
        if P.stagnation and g - last_imp >= P.stagnation:
            break
        if P.target is not None and best.obj <= P.target + 1e-9 and best.feasible:
            break
        A, B = E.rng.sample(pop, 2) if len(pop) > 1 else (pop[0], pop[0])
        kids = E.crossover(A, B) if E.rng.random() < P.pc else [A.copy(), B.copy()]
        for c in kids:
            if E.rng.random() < P.pm:
                E.mutate(c)
            if E.rng.random() < P.p_ls:
                E.local_search(c)
            ks = {s.key() for s in pop}
            order = sorted(range(len(pop)), key=lambda x: pop[x].fit)
            worst = order[-1] if len(pop) > P.n_elite else None
            if worst is not None and c.key() not in ks and c.fit < pop[worst].fit:
                pop[worst] = c
                if c.fit < best.fit - 1e-9:
                    best = c.copy(); last_imp = g
        trace.append(best.obj); times.append(time.time() - t0)
    return dict(obj=best.obj, feasible=best.feasible, time=time.time() - t0, gens=g, evals=E.nev,
                trace=trace, times=times, solution=sol_to_dict(inst, best), sol=best)


def sol_to_dict(inst, s):
    nJ = inst.nJ
    eff = []
    for i, q in enumerate(s.seq):
        prev, after_pm = -1, False
        for a in q:
            if a < nJ:
                sv = inst.mds[i][a] if prev < 0 else inst.sds[i][prev][a]
                if s.assist is not None and s.assist[a] and not after_pm and sv > 0:
                    eff.append(a)
                prev, after_pm = a, False
            else:
                after_pm = True
    return dict(seq=[q[:] for q in s.seq], pm_day={k: s.pm_day[k] for k in range(inst.nK)}, assist=sorted(eff))


def make_sol(inst, P, seq, pm_day, assist_jobs=()):
    """Reconstruit/évalue une solution externe (ex. issue de Gurobi) avec le décodeur du HGA."""
    E = Engine(inst, P)
    s = Sol()
    s.seq = [list(q) for q in seq]
    s.pm_day = [pm_day[k] if isinstance(pm_day, (list, tuple)) else pm_day[k] for k in range(inst.nK)]
    s.assist = [j in set(assist_jobs) for j in range(inst.nJ)] if P.objective == "assist" else None
    E.evaluate(s)
    return s


def schedule(inst, P, sol):
    """Dates détaillées : par machine [(activité, début setup, début traitement, fin)]."""
    out = []
    for i, q in enumerate(sol.seq):
        t = inst.R[i]; prev = -1; after_pm = False; rows = []
        for a in q:
            if a < inst.nJ:
                s = inst.mds[i][a] if prev < 0 else inst.sds[i][prev][a]
                if sol.assist is not None and sol.assist[a] and not after_pm and s > 0:
                    s *= (1 - P.delta)
                rows.append((f"J{a}", t, t + s, t + s + inst.p[i][a])); t += s + inst.p[i][a]
                prev, after_pm = a, False
            else:
                k = a - inst.nJ; rel, _ = inst.windows[sol.pm_day[k]]
                st = max(t + inst.spm[i][k], rel)
                rows.append((f"PM{k}", t, st, st + inst.pm[i][k])); t = st + inst.pm[i][k]; after_pm = True
        out.append(rows)
    return out
