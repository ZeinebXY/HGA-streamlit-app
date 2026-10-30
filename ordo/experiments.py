"""experiments.py - comparaison Gurobi / HGA, paramétrage du HGA, scénarios d'assistance, référence RPD.
Sous-commandes : check | compare | tune | scenarios | rpd     (voir README.md)
"""
import argparse, csv, glob, itertools, math, os, statistics as st, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instance import load_instance
from hga import HGAParams, run_hga, make_sol, Engine, Sol

OBJS = ("makespan", "weighted", "assist")


# ============================================================ outils communs
def add_common(p):
    g = p.add_argument_group("instances")
    g.add_argument("--files", nargs="+", required=True, help="fichiers ou motifs (ex. Solver/Data_3_*.txt)")
    g.add_argument("--days", type=int, default=None, help="nb de jours-fenêtres PM (auto : 7 Solver, Table 2 Factory)")
    g.add_argument("--resources", type=int, default=None, help="techniciens par jour (auto : 1 ; 2 pour Factory 2,3,4,6)")
    g.add_argument("--no-due", action="store_true", help="pas d'échéances (retard = 0). Les fichiers publics n'en contiennent pas")
    g.add_argument("--due-low", type=float, default=0.4)
    g.add_argument("--due-seed", type=int, default=0)
    g = p.add_argument_group("objectifs")
    g.add_argument("--objective", nargs="+", default=["makespan", "weighted", "assist"], choices=OBJS)
    g.add_argument("--alpha", type=float, default=1.0); g.add_argument("--beta", type=float, default=1.0)
    g.add_argument("--K", type=int, default=1); g.add_argument("--delta", type=float, default=0.5)
    g.add_argument("--gamma", type=float, default=0.2); g.add_argument("--c-ass", type=float, default=1.0)
    g = p.add_argument_group("HGA")
    g.add_argument("--runs", type=int, default=10); g.add_argument("--workers", type=int, default=4)
    g.add_argument("--pop", type=int, default=10); g.add_argument("--gmax", type=int, default=300)
    g.add_argument("--time", type=float, default=None, help="limite de temps par run (s)")
    g.add_argument("--n-mut", type=int, default=1); g.add_argument("--pm", type=float, default=1.0)
    g.add_argument("--pc", type=float, default=1.0)
    g.add_argument("--p-ls", type=float, default=1.0); g.add_argument("--n-ls", type=int, default=50)
    g.add_argument("--d-ins", type=float, default=1.0); g.add_argument("--d-swap", type=float, default=1.0)
    g.add_argument("--n-elite", type=int, default=1)
    g.add_argument("--crossover", default="one_point", choices=["one_point", "uniform"])
    g.add_argument("--mut-ops", nargs="+", default=["worst_machine"])
    g.add_argument("--stagnation", type=int, default=None)
    g = p.add_argument_group("Gurobi")
    g.add_argument("--no-milp", action="store_true"); g.add_argument("--milp-time", type=float, default=600)
    g.add_argument("--warm-start", action="store_true"); g.add_argument("--threads", type=int, default=0)
    p.add_argument("--out", default="results")


def expand(files):
    out = []
    for f in files:
        out += sorted(glob.glob(f)) or [f]
    return out


def loadkw(a):
    return dict(days=a.days, resources=a.resources, due_mode="none" if a.no_due else "gen",
                due_low=a.due_low, due_seed=a.due_seed)


def pdict(a, objective, **over):
    d = dict(objective=objective, alpha=a.alpha, beta=a.beta, K=(a.K if objective == "assist" else 0),
             delta=a.delta, gamma=a.gamma, c_ass=a.c_ass, pop=a.pop, gmax=a.gmax, n_mut=a.n_mut, pm=a.pm, pc=a.pc,
             p_ls=a.p_ls, n_ls=a.n_ls, d_ins=a.d_ins, d_swap=a.d_swap, n_elite=a.n_elite, crossover=a.crossover,
             mut_ops=tuple(a.mut_ops), time_limit=a.time, stagnation=a.stagnation)
    d.update(over)
    if isinstance(d["mut_ops"], str):
        d["mut_ops"] = tuple(d["mut_ops"].split("+"))
    return d


def _job(args):
    path, lkw, pd, seed = args
    inst = load_instance(path, **lkw)
    r = run_hga(inst, HGAParams(**pd), seed=seed)
    return dict(obj=r["obj"], feasible=r["feasible"], time=r["time"], evals=r["evals"], trace=r["trace"],
                solution=r["solution"])


def run_batch(path, lkw, pd, runs, workers):
    jobs = [(path, lkw, pd, s) for s in range(runs)]
    if workers <= 1:
        return [_job(j) for j in jobs]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_job, jobs))


def metrics(vals, B):
    """B = meilleure valeur connue ; RPD = (A-B)/B*100"""
    rpd = [(v - B) / B * 100 if B else 0.0 for v in vals]
    return dict(best=min(vals), mean=st.mean(vals), worst=max(vals), sd=st.pstdev(vals) if len(vals) > 1 else 0.0,
                arpd=st.mean(rpd), rpd_worst=max(rpd), success=100.0 * sum(v <= B * (1 + 1e-6) + 1e-9 for v in vals) / len(vals))


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)


def write_md(path, rows, cols):
    fmt = lambda v: f"{v:.4g}" if isinstance(v, float) else str(v)
    with open(path, "w") as f:
        f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
        for r in rows:
            f.write("| " + " | ".join(fmt(r.get(c, "")) for c in cols) + " |\n")


def plot_convergence(path, runs, title):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    L = max(len(r["trace"]) for r in runs)
    M = [r["trace"] + [r["trace"][-1]] * (L - len(r["trace"])) for r in runs]
    mean = [st.mean(c) for c in zip(*M)]
    plt.figure(figsize=(6, 4))
    plt.fill_between(range(L), [min(c) for c in zip(*M)], [max(c) for c in zip(*M)], alpha=.25)
    plt.plot(mean, label="moyenne"); plt.xlabel("génération"); plt.ylabel("meilleur objectif"); plt.title(title)
    plt.legend(); plt.tight_layout(); plt.savefig(path, dpi=130); plt.close()


def exact(inst, obj, a, warm=None):
    from milp_gurobi import solve_milp
    return solve_milp(inst, obj, alpha=a.alpha, beta=a.beta, K=a.K, delta=a.delta, gamma=a.gamma, c_ass=a.c_ass,
                      time_limit=a.milp_time, threads=a.threads, warm=warm)


# ============================================================ check
def cmd_check(a):
    for f in expand(a.files):
        inst = load_instance(f, **loadkw(a))
        print(f"{inst.name}: M={inst.nM} J={inst.nJ} PM={inst.nK} jours={inst.nD} w={inst.w[0]}  "
              f"R[0]={inst.R[0]:.2f} due[0]={inst.due[0]:.1f}")
        for obj in a.objective:
            r = run_hga(inst, HGAParams(**pdict(a, obj)), seed=0)
            print(f"   HGA {obj:9s} obj={r['obj']:.4f} faisable={r['feasible']} t={r['time']:.2f}s evals={r['evals']}")


# ============================================================ compare
def cmd_compare(a):
    rows = []
    for f in expand(a.files):
        lkw = loadkw(a)
        inst = load_instance(f, **lkw)
        for obj in a.objective:
            pd = pdict(a, obj)
            ex, warm = None, None
            if a.warm_start and not a.no_milp:
                warm = run_hga(inst, HGAParams(**pd), seed=999)["solution"]
            if not a.no_milp:
                ex = exact(inst, obj, a, warm)
            runs = run_batch(f, lkw, pd, a.runs, a.workers)
            vals = [r["obj"] for r in runs]
            Zx = ex["obj"] if ex and ex["obj"] is not None else None
            B = min([v for v in vals] + ([Zx] if Zx is not None else []))
            m = metrics(vals, B)
            row = dict(instance=inst.name, objective=obj, nM=inst.nM, nJ=inst.nJ, nK=inst.nK,
                       Z_exact=Zx, exact_proven=(ex or {}).get("proven_optimal"), bound=(ex or {}).get("bound"),
                       gurobi_gap_pct=(ex or {}).get("gap"), t_exact_s=(ex or {}).get("runtime"),
                       t_best_incumbent_s=(ex or {}).get("time_to_best"), B_ref=B, **m,
                       gap_best_vs_exact_pct=(100 * (m["best"] - Zx) / Zx if Zx else None),
                       time_mean=st.mean(r["time"] for r in runs), evals_mean=st.mean(r["evals"] for r in runs))
            rows.append(row)
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
            os.makedirs(a.out, exist_ok=True)
            plot_convergence(os.path.join(a.out, f"convergence_{obj}_{inst.name}.png"), runs, f"{inst.name} - {obj}")
    write_csv(os.path.join(a.out, "compare.csv"), rows)
    write_md(os.path.join(a.out, "compare.md"), rows, ["instance", "objective", "Z_exact", "exact_proven", "gurobi_gap_pct",
             "t_exact_s", "best", "gap_best_vs_exact_pct", "mean", "sd", "arpd", "success", "time_mean"])
    print(f"-> {a.out}/compare.csv, compare.md, convergence_*.png")


# ============================================================ tune
GRID = dict(pop=[10, 20, 50, 100], n_mut=[1, 2, 3, 5, 8], pm=[0.1, 0.3, 0.5, 1.0], p_ls=[0.0, 0.1, 0.3, 0.5, 1.0],
            n_ls=[1, 5, 20, 50], d_ins=[0.5, 0.8, 1.0], d_swap=[0.5, 0.8, 1.0], gmax=[100, 300, 500, 1000],
            pc=[0.5, 0.8, 1.0], n_elite=[1, 2, 5], crossover=["one_point", "uniform"],
            mut_ops=["worst_machine", "worst_machine+swap", "worst_machine+insert", "swap+insert",
                     "worst_machine+swap+insert+pm_day"])


def cmd_tune(a):
    grid = dict(GRID)
    for g in a.grid or []:
        k, v = g.split("=")
        grid[k] = [x if k in ("crossover", "mut_ops") else (float(x) if "." in x else int(x)) for x in v.split(",")]
    files = expand(a.files)
    for obj in a.objective:
        configs, allv = [], {}
        if a.mode == "ofat":
            configs = [(p, v, {p: v}) for p in a.params for v in grid[p]]
        else:   # plan factoriel complet à 2 niveaux (bas/haut = 1er et dernier de la grille)
            for combo in itertools.product(*[(grid[p][0], grid[p][-1]) for p in a.params]):
                configs.append(("factorial", combo, dict(zip(a.params, combo))))
        res = {}
        for (name, val, over) in configs:
            for f in files:
                runs = run_batch(f, loadkw(a), pdict(a, obj, **over), a.runs, a.workers)
                res[(name, str(val), f)] = runs
                allv.setdefault(f, []).extend(r["obj"] for r in runs)
                print(obj, name, val, os.path.basename(f), round(min(r["obj"] for r in runs), 4), flush=True)
        B = {f: min(v) for f, v in allv.items()}      # meilleure valeur connue (toutes configs)
        rows = []
        for (name, val, over) in configs:
            sub = [m for f in files for m in [metrics([r["obj"] for r in res[(name, str(val), f)]], B[f])]]
            tm = [st.mean(r["time"] for r in res[(name, str(val), f)]) for f in files]
            rows.append(dict(objective=obj, param=name, value=str(val), arpd=st.mean(s["arpd"] for s in sub),
                             success=st.mean(s["success"] for s in sub), sd=st.mean(s["sd"] for s in sub),
                             best_mean=st.mean(s["best"] for s in sub), time_mean=st.mean(tm)))
        write_csv(os.path.join(a.out, f"tune_{obj}.csv"), rows)
        write_md(os.path.join(a.out, f"tune_{obj}.md"), rows, ["param", "value", "arpd", "success", "sd", "time_mean"])
        if a.mode == "factorial":
            eff = []
            for n, p in enumerate(a.params):
                lo = [r["arpd"] for r, c in zip(rows, configs) if c[1][n] == grid[p][0]]
                hi = [r["arpd"] for r, c in zip(rows, configs) if c[1][n] == grid[p][-1]]
                eff.append(dict(param=p, low=grid[p][0], high=grid[p][-1], arpd_low=st.mean(lo), arpd_high=st.mean(hi),
                                effect=st.mean(hi) - st.mean(lo)))
            write_csv(os.path.join(a.out, f"doe_effects_{obj}.csv"), eff)
            print("effets principaux (ARPD haut - bas ; négatif = niveau haut meilleur) :")
            for e in sorted(eff, key=lambda e: -abs(e["effect"])):
                print("  ", e)
        else:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            for p in a.params:
                rr = [r for r in rows if r["param"] == p]
                plt.figure(figsize=(5, 3.5)); plt.plot([r["value"] for r in rr], [r["arpd"] for r in rr], "o-")
                plt.xlabel(p); plt.ylabel("ARPD (%)"); plt.title(f"{obj} - effet de {p}"); plt.tight_layout()
                plt.savefig(os.path.join(a.out, f"tune_{obj}_{p}.png"), dpi=130); plt.close()
        print(open(os.path.join(a.out, f"tune_{obj}.md")).read())


# ============================================================ scenarios (assistance)
def cmd_scenarios(a):
    rows = []
    for f in expand(a.files):
        lkw = loadkw(a); inst = load_instance(f, **lkw)
        for K in a.Ks:
            for dl in (a.deltas if K > 0 else [a.deltas[0]]):
                for gm in (a.gammas if K > 0 else [a.gammas[0]]):
                    pd = pdict(a, "assist", K=K, delta=dl, gamma=gm)
                    runs = run_batch(f, lkw, pd, a.runs, a.workers)
                    best = min(runs, key=lambda r: r["obj"])
                    s = best["solution"]
                    sol = make_sol(inst, HGAParams(**pd), s["seq"], [s["pm_day"][k] for k in range(inst.nK)], s["assist"])
                    row = dict(instance=inst.name, K=K, delta=dl, gamma=gm, HGA_best=best["obj"],
                               HGA_mean=st.mean(r["obj"] for r in runs), TMCT=sum(m[0] for m in sol.mv),
                               TT=sum(m[1] for m in sol.mv), assist_cost=sum(m[3] for m in sol.mv),
                               n_assisted=len(s["assist"]), time_hga=st.mean(r["time"] for r in runs))
                    if not a.no_milp and inst.nJ <= a.milp_max_jobs:
                        from milp_gurobi import solve_milp
                        ex = solve_milp(inst, "assist", alpha=a.alpha, beta=a.beta, K=K, delta=dl, gamma=gm, c_ass=a.c_ass,
                                        time_limit=a.milp_time, threads=a.threads, warm=s)
                        row.update(Z_exact=ex["obj"], gurobi_status=ex["status_name"], gurobi_gap_pct=ex["gap"], t_exact=ex["runtime"])
                    rows.append(row); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    write_csv(os.path.join(a.out, "scenarios.csv"), rows)
    write_md(os.path.join(a.out, "scenarios.md"), rows, ["instance", "K", "delta", "gamma", "HGA_best", "TMCT", "TT",
             "assist_cost", "n_assisted", "Z_exact", "gurobi_status", "t_exact"])


# ============================================================ RPD : référence = solution fournie (RPD Solutions)
def read_reference(inst, path):
    seq = []
    for l in open(path, newline="").read().replace("\r", "").split("\n"):
        if l.strip() or len(seq) < inst.nM:
            seq.append([int(float(x)) for x in l.split(";") if x.strip() != ""])
    return seq[:inst.nM]


def best_days(inst, P, seq):
    """jours de PM optimaux pour des séquences données (énumération ; glouton si trop grand)."""
    E = Engine(inst, P)
    pms = [k for k in range(inst.nK)]
    best = None
    if inst.nD ** len(pms) <= 60000:
        for combo in itertools.product(range(inst.nD), repeat=len(pms)):
            if any(sum(1 for d in combo if d == x) > inst.w[x] for x in range(inst.nD)):
                continue
            s = Sol(); s.seq = [q[:] for q in seq]; s.pm_day = list(combo); s.assist = None
            E.evaluate(s)
            if best is None or s.fit < best.fit:
                best = s
    else:
        s = Sol(); s.seq = [q[:] for q in seq]; s.pm_day = [0] * inst.nK; s.assist = None
        for k in pms:
            cand = []
            for d in range(inst.nD):
                s.pm_day[k] = d; E.evaluate(s); cand.append((s.fit, d))
            s.pm_day[k] = min(cand)[1]
        best = E.evaluate(s)
    return best


def cmd_rpd(a):
    rows = []
    for f in expand(a.files):
        lkw = loadkw(a); inst = load_instance(f, **lkw)
        num = os.path.basename(f).split("_")[0]
        ref = os.path.join(a.ref_dir, f"{num}_Sequence.txt")
        if not os.path.exists(ref):
            print("pas de solution de référence pour", f); continue
        pd = pdict(a, "weighted")
        rs = best_days(inst, HGAParams(**pd), read_reference(inst, ref))
        B = rs.obj
        runs = run_batch(f, lkw, pd, a.runs, a.workers)
        vals = [r["obj"] for r in runs]
        rr = metrics(vals, B)
        row = dict(instance=inst.name, B_ref=B, ref_TMCT=sum(m[0] for m in rs.mv), ref_TT=sum(m[1] for m in rs.mv),
                   ref_feasible=rs.feasible, **{k: rr[k] for k in ("best", "mean", "worst", "sd")},
                   rpd_best=100 * (rr["best"] - B) / B, arpd=rr["arpd"], time_mean=st.mean(r["time"] for r in runs))
        rows.append(row); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    write_csv(os.path.join(a.out, "rpd.csv"), rows)
    write_md(os.path.join(a.out, "rpd.md"), rows, ["instance", "B_ref", "ref_TMCT", "ref_TT", "best", "mean", "rpd_best", "arpd", "time_mean"])


# ============================================================ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n, fn in (("check", cmd_check), ("compare", cmd_compare), ("tune", cmd_tune), ("scenarios", cmd_scenarios), ("rpd", cmd_rpd)):
        p = sub.add_parser(n); add_common(p); p.set_defaults(fn=fn)
        if n == "tune":
            p.add_argument("--params", nargs="+", default=["n_mut", "p_ls"]); p.add_argument("--mode", default="ofat", choices=["ofat", "factorial"])
            p.add_argument("--grid", nargs="*", help="surcharge : n_mut=1,2,10")
        if n == "scenarios":
            p.add_argument("--Ks", type=int, nargs="+", default=[0, 1, 2, 3]); p.add_argument("--deltas", type=float, nargs="+", default=[0.5])
            p.add_argument("--gammas", type=float, nargs="+", default=[0.2]); p.add_argument("--milp-max-jobs", type=int, default=12)
        if n == "rpd":
            p.add_argument("--ref-dir", required=True, help='dossier "RPD Solutions"')
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
