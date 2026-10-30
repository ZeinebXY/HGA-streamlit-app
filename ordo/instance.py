"""instance.py - lecture des instances du dépôt « Integrated_scheduling_problem_instances »
(dossiers Solver/ et Factory/) + sections du format :
R (temps résiduel par machine), P, PM, ELEG, ELEG_PM, MDS, SDS (M_0..M_x), S_PM.
Unités : heures. Le planning démarre à 00:00 ; une PM n'est possible que dans les fenêtres
journalières [day_len*d + win_start ; day_len*d + win_end] (6h-20h dans l'article), w ressources / jour.

ATTENTION : les fichiers publics NE CONTIENNENT PAS les dates d'échéance des jobs.
-> due_mode="gen" (défaut) fabrique des échéances reproductibles (graine due_seed) ;
   due_mode="none" met des échéances infinies (retard toujours nul).
"""
import os, re, random
from dataclasses import dataclass, field

# Table 2 de l'article : horizon (nb de jours-fenêtres) des instances Factory ; 2 ressources pour 2,3,4,6
FACTORY_HORIZON = {1: 6, 2: 7, 3: 5, 4: 6, 5: 8, 6: 6, 7: 8, 8: 6, 9: 6, 10: 8, 11: 7, 12: 7, 13: 4,
                   14: 7, 15: 7, 16: 6, 17: 6, 18: 4, 19: 6, 20: 5, 21: 5, 22: 7, 23: 6, 24: 4, 25: 6}
FACTORY_RES2 = {2, 3, 4, 6}
FACTORY_DAYS_DEFAULT = 12


@dataclass
class Instance:
    name: str
    nM: int
    nJ: int
    nK: int
    R: list            # R[i]            : machine i chargée jusqu'à R[i]
    p: list            # p[i][j]         : durée du job j sur i
    pm: list           # pm[i][k]        : durée de la PM k sur i
    eleg: list         # eleg[i][j]
    eleg_pm: list      # eleg_pm[i][k]
    mds: list          # mds[i][j]       : setup si j est le 1er sur i
    sds: list          # sds[i][a][b]    : setup a -> b sur i
    spm: list          # spm[i][k]       : setup avant PM k sur i
    windows: list      # windows[d] = (release, due) de la fenêtre du jour d
    w: list            # w[d]            : nb de techniciens le jour d
    due: list          # due[j]
    job_machines: list = field(default_factory=list)
    pm_machines: list = field(default_factory=list)

    @property
    def nD(self):
        return len(self.windows)

    def finalize(self):
        self.job_machines = [[i for i in range(self.nM) if self.eleg[i][j] > 0.5] for j in range(self.nJ)]
        self.pm_machines = [[i for i in range(self.nM) if self.eleg_pm[i][k] > 0.5] for k in range(self.nK)]
        return self


def _parse_file(path):
    txt = open(path, newline="").read().replace("\r", "")
    lines = [l.strip() for l in txt.split("\n")]
    nM, nJ, nK = [int(float(x)) for x in lines[1].strip(";").split(";")]
    data, sds, sec = {}, [], None
    for l in lines[2:]:
        if not l:
            continue
        if re.match(r"^[A-Za-z]", l):
            if l.startswith("M_"):
                sds.append([])
            else:
                sec = l
                data[sec] = []
            continue
        row = [float(x) for x in l.split(";") if x != ""]
        (sds[-1] if sec == "SDS" else data[sec]).append(row)
    return nM, nJ, nK, data, sds


def load_instance(path, days=None, resources=None, win_start=6.0, win_end=20.0, day_len=24.0,
                  due_mode="gen", due_low=0.4, due_high=1.0, due_seed=0):
    """days/resources=None : auto (Factory -> 12 jours, 2 ressources pour les instances 2,3,4,6 ; Solver -> 7 jours, 1 ressource)."""
    name = os.path.splitext(os.path.basename(path))[0]
    nM, nJ, nK, d, sds = _parse_file(path)
    m = re.match(r"^(\d+)_Data", name)
    if days is None:
        # Factory : les solutions de référence placent les PM aux jours 7-8, au-delà de l'« Horizon » de la Table 2 ;
        # les vraies fenêtres ne sont pas dans les fichiers -> 12 jours de fenêtres (non bloquant). Solver : 7 jours.
        days = FACTORY_DAYS_DEFAULT if m else 7
    if resources is None:
        resources = 2 if (m and int(m.group(1)) in FACTORY_RES2) else 1
    inst = Instance(name, nM, nJ, nK, d["R"][0], d["P"], d["PM"], d["ELEG"], d["ELEG_PM"], d["MDS"], sds,
                    d["S_PM"], [(day_len * k + win_start, day_len * k + win_end) for k in range(days)],
                    [resources] * days, [], )
    inst.finalize()
    if due_mode == "none":
        inst.due = [1e12] * nJ
    else:  # échéances fabriquées : H * U(due_low, due_high)
        rng = random.Random(due_seed)
        mean_p = [sum(inst.p[i][j] for i in inst.job_machines[j]) / len(inst.job_machines[j]) for j in range(nJ)]
        H = sum(inst.R) / nM + sum(mean_p) / nM
        inst.due = [H * rng.uniform(due_low, due_high) for _ in range(nJ)]
    if nK > days * resources:
        print(f"[!] {name}: {nK} PM > {days*resources} créneaux : instance infaisable")
    return inst
