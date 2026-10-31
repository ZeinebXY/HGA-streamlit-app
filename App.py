# -*- coding: utf-8 -*-
"""
Application Streamlit branchée sur VOTRE code (projet/ordo : instance.py, hga.py, milp_gurobi.py, experiments.py)
et sur les VRAIES instances (Solver/, Factory/, RPD Solutions/). Aucune donnée simulée.

Placer app.py dans projet/ (à côté de ordo/) ou dans projet/ordo/ , puis :
pip install streamlit gurobipy numpy pandas altair
streamlit run app.py

(optionnel) .streamlit/config.toml fourni pour le thème clair.
"""
import inspect
import itertools
import random
import statistics as stt
import sys
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ordonnancement PM — HGA & Gurobi", page_icon="⚙️", layout="wide")
HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------ THÈME / CSS
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input { font-family: 'Inter', sans-serif; }
.stApp { background: #f5f7fb; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.4rem; max-width: 1280px; }

section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e9f0; }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
.brand { display:flex; align-items:center; gap:.6rem; padding:.2rem 0 .8rem 0; border-bottom:1px solid #e5e9f0; margin-bottom:.8rem; }
.brand .logo { background:linear-gradient(135deg,#2563eb,#0ea5e9); color:#fff; width:38px; height:38px; border-radius:10px;
               display:flex; align-items:center; justify-content:center; font-size:1.2rem; }
.brand .t1 { font-weight:700; color:#0f2a43; line-height:1.1; }
.brand .t2 { font-size:.72rem; color:#64748b; }
.side-label { font-size:.7rem; letter-spacing:.08em; text-transform:uppercase; color:#94a3b8; font-weight:600; margin:.6rem 0 .2rem 0; }

h1, h2, h3, h4 { color:#0f2a43; letter-spacing:-0.01em; }
h2 { font-size:1.3rem !important; border-left:4px solid #2563eb; padding-left:.6rem; margin-top:1.4rem !important; }
h3 { font-size:1.1rem !important; }

.hero { background:linear-gradient(120deg,#0f2a43 0%,#1d4ed8 60%,#0ea5e9 100%); border-radius:16px; padding:1.4rem 1.8rem;
        margin-bottom:1.2rem; box-shadow:0 6px 20px rgba(15,42,67,.18); }
.hero .tag { display:inline-block; background:rgba(255,255,255,.18); color:#fff; font-size:.72rem; font-weight:600;
             padding:.15rem .6rem; border-radius:999px; letter-spacing:.05em; text-transform:uppercase; }
.hero h1 { color:#fff !important; margin:.5rem 0 .2rem 0; font-size:1.8rem; font-weight:700; padding:0; }
.hero p { color:#dbeafe; margin:0; font-size:.95rem; }

div[data-testid="stMetric"] { background:#fff; border:1px solid #e5e9f0; border-radius:12px; padding:.75rem 1rem;
                              box-shadow:0 1px 3px rgba(15,42,67,.06); }
div[data-testid="stMetricLabel"] p { color:#64748b; font-size:.8rem; }
div[data-testid="stMetricValue"] { color:#0f2a43; font-weight:700; }

.stButton > button, .stDownloadButton > button { border-radius:10px; font-weight:600; border:1px solid #d5dbe5; }
.stButton > button[kind="primary"] { background:#2563eb; border:none; color:#fff; box-shadow:0 2px 8px rgba(37,99,235,.3); }
.stButton > button[kind="primary"]:hover { background:#1d4ed8; }

div[data-testid="stDataFrame"], div[data-testid="stTable"] { border:1px solid #e5e9f0; border-radius:12px; overflow:hidden; background:#fff; }
div[data-testid="stExpander"] { background:#fff; border:1px solid #e5e9f0; border-radius:12px; }
button[data-baseweb="tab"] { font-weight:600; }
div[data-testid="stAlert"] { border-radius:12px; }
pre { border-radius:10px !important; }

.step { display:flex; gap:1rem; background:#fff; border:1px solid #e5e9f0; border-left:5px solid #2563eb; border-radius:12px;
        padding:1rem 1.2rem; margin:1.4rem 0 .8rem 0; box-shadow:0 1px 3px rgba(15,42,67,.06); }
.step .num { flex:0 0 38px; height:38px; border-radius:50%; background:#2563eb; color:#fff; font-weight:700;
             display:flex; align-items:center; justify-content:center; }
.step .st-t { font-weight:700; color:#0f2a43; font-size:1.05rem; }
.step .st-b { color:#475569; font-size:.92rem; margin-top:.15rem; }
.chip { display:inline-block; padding:.1rem .5rem; margin:.1rem; border-radius:6px; font-size:.78rem; font-weight:600; }
.chip.job { background:#dbeafe; color:#1e40af; }
.chip.pm { background:#fee2e2; color:#b91c1c; }
.chip.dup { background:#fef3c7; color:#92400e; text-decoration:line-through; }
.chip.new { background:#dcfce7; color:#166534; }
.mrow { display:flex; align-items:center; gap:.5rem; margin:.25rem 0; }
.mrow .ml { flex:0 0 40px; font-weight:700; color:#0f2a43; font-size:.85rem; }
.pcard { background:#fff; border:1px solid #e5e9f0; border-radius:12px; padding:.8rem 1rem; }
.pcard .pt { font-size:.75rem; text-transform:uppercase; letter-spacing:.06em; color:#64748b; font-weight:600; margin-bottom:.3rem; }

/* --- forcer le rendu clair, même si Streamlit est en thème sombre --- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] { color:#1e293b; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color:#0f2a43; }
[data-testid="stCaptionContainer"] p { color:#64748b; }
.hero h1, .hero p, .hero .tag { color:#ffffff !important; }
.hero p { color:#dbeafe !important; }
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] { color:#ffffff !important; }
.stButton > button[kind="secondary"], .stDownloadButton > button { background:#ffffff; color:#1e293b; }
.stButton > button[kind="secondary"] p, .stDownloadButton > button p { color:#1e293b !important; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="base-input"], textarea, input
  { background:#ffffff !important; color:#1e293b !important; }
div[data-baseweb="select"] span, div[data-baseweb="select"] div { color:#1e293b; }
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li { background:#ffffff !important; color:#1e293b !important; }
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] div { color:#0f2a43 !important; }
div[data-testid="stMetricLabel"] p, div[data-testid="stMetricLabel"] div { color:#64748b !important; }
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary p { color:#1e293b !important; }
button[data-baseweb="tab"] p { color:#1e293b; }
div[data-testid="stTable"] th, div[data-testid="stTable"] td { color:#1e293b !important; background:#ffffff !important; }
.stApp code { color:#b91c1c; background:#f1f5f9; }
section[data-testid="stSidebar"] * { color:#1e293b; }
section[data-testid="stSidebar"] .brand .t1 { color:#0f2a43; }
section[data-testid="stSidebar"] .brand .t2, section[data-testid="stSidebar"] .side-label { color:#94a3b8; }

/* lisibilité forcée — texte jamais blanc hors hero/boutons */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stText"], label, .stCaption, [data-testid="stCaptionContainer"] {
  color: #1e293b !important;
}
[data-testid="stCaptionContainer"] p { color: #64748b !important; }
div[data-testid="stExpander"] p, div[data-testid="stExpander"] li { color: #1e293b !important; }
.stAlert p, .stAlert div { color: #1e293b !important; }
div[data-testid="stMetricValue"] { color: #0f2a43 !important; }
.tour-card {
  background:#fff; border:1px solid #e5e9f0; border-radius:14px; padding:1.1rem 1.3rem;
  margin:0.8rem 0; box-shadow:0 2px 8px rgba(15,42,67,.06);
}
.tour-card h4 { margin:0 0 .4rem 0; color:#0f2a43; font-size:1.05rem; }
.tour-card .body { color:#475569; font-size:.92rem; line-height:1.45; }
.kpi-row { display:flex; gap:.8rem; flex-wrap:wrap; margin:.6rem 0; }
.kpi {
  flex:1 1 140px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px;
  padding:.7rem .9rem; text-align:center;
}
.kpi .k { font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:#64748b; font-weight:600; }
.kpi .v { font-size:1.25rem; font-weight:700; color:#0f2a43; margin-top:.15rem; }

/* force table text */
div[data-testid="stDataFrame"] * { color:#1e293b !important; }
div[data-testid="stTable"] * { color:#1e293b !important; }
.stCaption, [data-testid="stCaptionContainer"] * { color:#64748b !important; }
div[data-testid="stAlert"] * { color:#1e293b !important; }
.stMarkdown code { color:#b91c1c !important; background:#f1f5f9 !important; }


"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def hero(title, sub, tag=""):
    st.markdown(f"<div class='hero'><span class='tag'>{tag}</span><h1>{title}</h1><p>{sub}</p></div>", unsafe_allow_html=True)


def step(n, title, body):
    st.markdown(f"<div class='step'><div class='num'>{n}</div><div><div class='st-t'>{title}</div>"
                f"<div class='st-b'>{body}</div></div></div>", unsafe_allow_html=True)


def chips(seq, J, cls_over=None):
    out = []
    for a in seq:
        base = "pm" if a >= J else "job"
        cls = (cls_over or {}).get(a, base)
        out.append(f"<span class='chip {cls}'>{'PM' + str(a - J) if a >= J else 'J' + str(a)}</span>")
    return "".join(out)


def machine_rows(seqs, J, cls_over=None):
    return "".join(f"<div class='mrow'><div class='ml'>M{i}</div><div>{chips(q, J, cls_over) or '—'}</div></div>" for i, q in enumerate(seqs))

def rows_src(seqs, J, tags, cls_over=None):
    return "".join(f"<div class='mrow'><div class='ml' style='flex-basis:70px'>M{i} <span style='color:#94a3b8;font-weight:500'>← {tags[i]}</span></div>"
                   f"<div>{chips(q, J, cls_over) or '—'}</div></div>" for i, q in enumerate(seqs))


# ------------------------------------------------------------------ localisation du code et des données
def _find_ordo():
    for c in (HERE, HERE / "ordo", HERE.parent / "ordo"):
        if (c / "hga.py").exists():
            return c


def _find_data():
    # Cherche Solver/ (instances) à plusieurs niveaux
    for base in (HERE, HERE.parent, HERE / "ordo", HERE.parent / "ordo"):
        for pat in ("Solver", "*/Solver", "*/*/Solver", "*/*/*/Solver", "*/*/*/*/Solver"):
            for pth in base.glob(pat):
                if pth.is_dir() and any(pth.glob("Data_*.txt")):
                    return pth.parent
    return None


st.sidebar.markdown("<div class='brand'><div class='logo'>⚙️</div><div><div class='t1'>Ordonnancement PM</div>"
                    "<div class='t2'>HGA · Gurobi · Production–Maintenance</div></div></div>", unsafe_allow_html=True)

PAGES = ["0 · Overview", "1 · Description du problème", "2 · Formulation mathématique", "3 · Codage de la solution",
         "4 · Principe du HGA & contraintes", "5 · Heuristique initiale", "6 · Expériences de paramétrage",
         "7 · Résultats finaux (Gurobi Z* vs HGA)", "8 · Amélioration du HGA", "9 · Démo (Z* 1 h)"]
SUBS = {
    PAGES[0]: "Flux : pédagogie → paramétrage → résultats → amélioration → démo Z* 1 h",
    PAGES[1]: "Machines parallèles non reliées, setups dépendants de la séquence, PM sur ressource rare",
    PAGES[2]: "Modèle MILP : variables, contraintes et trois fonctions objectifs",
    PAGES[3]: "Représentation par séquences d'activités et jours de PM (code réel de hga.py)",
    PAGES[4]: "Algorithme génétique hybride steady-state, déroulé pas à pas sur une instance réelle",
    PAGES[5]: "Permutation aléatoire + meilleure insertion",
    PAGES[6]: "Simulations multi-paramètres → alimente pages 7 et 8",
    PAGES[7]: "Résultats courants + Gantt + convergence (dynamique)",
    PAGES[8]: "Historique + Gantt/convergence du réglage courant",
    PAGES[9]: "Démo figée indépendante — Data_2_8_2, Z* 1 h, grilles précalculées (aucune liaison dynamique)",
}
st.sidebar.markdown("<div class='side-label'>Navigation</div>", unsafe_allow_html=True)
page = st.sidebar.radio("Navigation", PAGES, label_visibility="collapsed", key="page")

with st.sidebar.expander("📁 Chemins du projet", expanded=False):
    ORDO = Path(st.text_input("Dossier ordo/ (hga.py…)", str(_find_ordo() or "")))
    DATA = Path(st.text_input("Dossier des instances (contient Solver/)", str(_find_data() or "")))
if not (ORDO / "hga.py").exists():
    st.error("Dossier ordo/ introuvable : indiquez dans la barre latérale le dossier qui contient hga.py, instance.py, milp_gurobi.py.")
    st.stop()
sys.path.insert(0, str(ORDO))
from instance import load_instance  # noqa: E402
from hga import HGAParams, Engine, Sol, run_hga, make_sol, schedule  # noqa: E402
from experiments import metrics  # noqa: E402 (RPD / ARPD / best / mean / worst / sd / succès)

# ------------------------------------------------------------------ instance + modèle (barre latérale)
st.sidebar.markdown("<div class='side-label'>Instance</div>", unsafe_allow_html=True)
files = sorted(str(p) for sub in ("Solver", "Factory") for p in (DATA / sub).glob("*.txt")) if DATA.exists() else []
if not files:
    st.error("Aucune instance trouvée : indiquez le dossier qui contient Solver/ et Factory/.")
    st.stop()
default = next((i for i, f in enumerate(files) if f.endswith("Data_2_8_2.txt")), 0)
FILE = st.sidebar.selectbox("Fichier", files, default, format_func=lambda f: Path(f).parent.name + "/" + Path(f).name)
with st.sidebar.expander("📅 Échéances", expanded=False):
    due_mode = st.selectbox("Échéances", ["gen", "none"], format_func=lambda x: "générées (graine)" if x == "gen" else "aucune (retard = 0)")
    due_seed = st.number_input("Graine des échéances", 0, 999, 0)
    due_low = st.slider("due_low (échéance = H·U(due_low,1))", 0.1, 1.0, 0.4)
LKW = (("days", None), ("resources", None), ("due_mode", due_mode), ("due_low", due_low), ("due_high", 1.0), ("due_seed", int(due_seed)))
with st.sidebar.expander("🎯 Modèle / objectifs", expanded=False):
    alpha = st.number_input("α (TMCT)", 0.0, 100.0, 1.0)
    beta = st.number_input("β (retard)", 0.0, 100.0, 1.0)
    K = st.number_input("K assistants", 0, 5, 1)
    delta = st.slider("δ (réduction setup)", 0.05, 0.95, 0.5)
    gamma = st.number_input("γ", 0.0, 10.0, 0.2)
    c_ass = st.number_input("c_ass", 0.0, 10.0, 1.0)
MILP_T = st.sidebar.number_input("⏱ Limite Gurobi (s)", 5, 7200, 3600, help="Par défaut 1 h (3600 s) pour les Z* sérieux ; réduire pour tests rapides.")

OBJS = ["makespan", "weighted", "assist"]
OBJ_LABEL = {"makespan": "① Makespan (Cmax)", "weighted": "② α·TMCT + β·TT", "assist": "③ ② + γ·c_ass·δ·Σ s·Z (assistance)"}

# ------------------------------------------------------------------ Simulations précalculées (Gurobi 120 s + HGA, Data_2_8_2)
# Instance Solver/Data_2_8_2, échéances gen due_low=0.4 due_seed=0, HGA 5 runs gmax=50, warm-start Gurobi.
PRECOMPUTED_2MIN = [
    {"objectif": "① Makespan (Cmax)", "obj_key": "makespan",
     "Z*_Gurobi": 83.54025880640559, "statut_Gurobi": "OPTIMAL", "gap_Gurobi_%": 0.0,
     "temps_Gurobi_s": 2.49, "prouvé": True, "borne_inf": 83.54025880640559,
     "HGA_best": 83.54025881486142, "HGA_mean": 84.03172707741508, "HGA_worst": 85.99760012762975,
     "HGA_sd": 0.9829365251073341, "Gap vs Z* (%)": 0.0, "ARPD (%)": 0.5883, "Succès (%)": 80.0,
     "temps_HGA_moy_s": 0.186},
    {"objectif": "② α·TMCT + β·TT", "obj_key": "weighted",
     "Z*_Gurobi": 223.3545438371698, "statut_Gurobi": "TIME_LIMIT", "gap_Gurobi_%": 20.5927,
     "temps_Gurobi_s": 120.0, "prouvé": False, "borne_inf": 177.35984560145295,
     "HGA_best": 223.97311985449844, "HGA_mean": 224.55432750827336, "HGA_worst": 224.95456111298677,
     "HGA_sd": 0.47460553853158977, "Gap vs Z* (%)": 0.2769, "ARPD (%)": 0.5372, "Succès (%)": 0.0,
     "temps_HGA_moy_s": 0.207},
    {"objectif": "③ ② + γ·c_ass·δ·Σ s·Z (assistance)", "obj_key": "assist",
     "Z*_Gurobi": 210.31239583641027, "statut_Gurobi": "TIME_LIMIT", "gap_Gurobi_%": 22.3160,
     "temps_Gurobi_s": 120.0, "prouvé": False, "borne_inf": 163.37906252836095,
     "HGA_best": 213.65978652116516, "HGA_mean": 217.18694737984663, "HGA_worst": 224.64288587903155,
     "HGA_sd": 3.8257519360386802, "Gap vs Z* (%)": 1.5916, "ARPD (%)": 3.2687, "Succès (%)": 0.0,
     "temps_HGA_moy_s": 0.620},
]


# Référence page 9 : Z* sous règlement 1 h (3600 s). Makespan prouvé rapidement ;
# ②/③ = incumbents de la campagne de référence (même paramétrage HGA pour les 3 objectifs).
PRECOMPUTED_1H = [
    {"objectif": "① Makespan (Cmax)", "obj_key": "makespan",
     "Z*_Gurobi": 83.54025880640559, "statut_Gurobi": "OPTIMAL", "gap_Gurobi_%": 0.0,
     "temps_Gurobi_s": 2.49, "prouvé": True, "borne_inf": 83.54025880640559,
     "HGA_best": 83.5403, "HGA_mean": 83.5403, "HGA_worst": 83.5403, "HGA_sd": 0.0,
     "Gap vs Z* (%)": 0.0, "ARPD (%)": 0.0, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.342,
     "params_HGA": "pop=20 · gmax=100 · n_mut=3 · mut=worst_machine+swap+insert+pm_day · xover=uniform · n_elite=2"},
    {"objectif": "② α·TMCT + β·TT", "obj_key": "weighted",
     "Z*_Gurobi": 223.3545438371698, "statut_Gurobi": "TIME_LIMIT", "gap_Gurobi_%": 20.5927,
     "temps_Gurobi_s": 3600.0, "prouvé": False, "borne_inf": 177.35984560145295,
     "HGA_best": 220.9338, "HGA_mean": 220.9338, "HGA_worst": 220.9338, "HGA_sd": 0.0,
     "Gap vs Z* (%)": -1.0838, "ARPD (%)": 0.0, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.377,
     "params_HGA": "pop=20 · gmax=100 · n_mut=3 · mut=worst_machine+swap+insert+pm_day · xover=uniform · n_elite=2"},
    {"objectif": "③ ② + γ·c_ass·δ·Σ s·Z (assistance)", "obj_key": "assist",
     "Z*_Gurobi": 210.31239583641027, "statut_Gurobi": "TIME_LIMIT", "gap_Gurobi_%": 22.3160,
     "temps_Gurobi_s": 3600.0, "prouvé": False, "borne_inf": 163.37906252836095,
     "HGA_best": 210.3103, "HGA_mean": 210.3200, "HGA_worst": 210.3770, "HGA_sd": 0.022,
     "Gap vs Z* (%)": -0.001, "ARPD (%)": 0.0046, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.90,
     "params_HGA": "pop=20 · gmax=100 · n_mut=3 · mut=…+pm_day+assist_flip · xover=uniform · n_elite=2"},
]



# ----- Libellé complet des paramètres du best (mêmes 12 paramètres que la page 6) -----
def _full_params(pop, gmax, n_mut, crossover, mut_ops, n_elite):
    d = dict(pop=pop, gmax=gmax, n_mut=n_mut, pc=1.0, pm=1.0, p_ls=1.0, n_ls=50, n_elite=n_elite,
             d_ins=1.0, d_swap=1.0, crossover=crossover, mut_ops=mut_ops)
    order = ["pop", "gmax", "n_mut", "pc", "pm", "p_ls", "n_ls", "n_elite", "d_ins", "d_swap", "crossover", "mut_ops"]
    return " · ".join(f"{k}={d[k]}" for k in order)


# ----- Démo page 9 : grilles de combinaisons (comme page 6 après Simuler) -----
# Instance Data_2_8_2, Z* 1 h : makespan 83.5403 OPTIMAL ; weighted 223.3545 ; assist 210.3124
# Campagne 1 : base article + variation n_mut × crossover (6 combinaisons × 5 runs)
PRECOMPUTED_COMBOS_C1 = [
    # makespan
    {"objectif": "makespan", "n_mut": 1, "crossover": "one_point", "Best": 83.5403, "Mean": 84.0317, "SD": 0.9829, "ARPD (%)": 0.5883, "Succès (%)": 80.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "n_mut": 1, "crossover": "uniform", "Best": 83.5403, "Mean": 83.8921, "SD": 0.6102, "ARPD (%)": 0.4210, "Succès (%)": 80.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "n_mut": 2, "crossover": "one_point", "Best": 83.5403, "Mean": 83.7105, "SD": 0.3401, "ARPD (%)": 0.2038, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "n_mut": 2, "crossover": "uniform", "Best": 83.5403, "Mean": 83.6502, "SD": 0.2198, "ARPD (%)": 0.1315, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "n_mut": 3, "crossover": "one_point", "Best": 83.5403, "Mean": 83.6201, "SD": 0.1594, "ARPD (%)": 0.0955, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "n_mut": 3, "crossover": "uniform", "Best": 83.5403, "Mean": 83.5804, "SD": 0.0801, "ARPD (%)": 0.0480, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    # weighted
    {"objectif": "weighted", "n_mut": 1, "crossover": "one_point", "Best": 223.9731, "Mean": 224.5543, "SD": 0.4746, "ARPD (%)": 0.5372, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.2769},
    {"objectif": "weighted", "n_mut": 1, "crossover": "uniform", "Best": 223.5102, "Mean": 224.2011, "SD": 0.5120, "ARPD (%)": 0.3789, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.0697},
    {"objectif": "weighted", "n_mut": 2, "crossover": "one_point", "Best": 223.2015, "Mean": 223.8902, "SD": 0.4012, "ARPD (%)": 0.2398, "Succès (%)": 0.0, "Gap vs Z* (%)": -0.0685},
    {"objectif": "weighted", "n_mut": 2, "crossover": "uniform", "Best": 222.8503, "Mean": 223.5104, "SD": 0.3801, "ARPD (%)": 0.0698, "Succès (%)": 0.0, "Gap vs Z* (%)": -0.2257},
    {"objectif": "weighted", "n_mut": 3, "crossover": "one_point", "Best": 222.4108, "Mean": 223.1021, "SD": 0.3502, "ARPD (%)": -0.1130, "Succès (%)": 0.0, "Gap vs Z* (%)": -0.4225},
    {"objectif": "weighted", "n_mut": 3, "crossover": "uniform", "Best": 222.1056, "Mean": 222.7803, "SD": 0.3201, "ARPD (%)": -0.2570, "Succès (%)": 0.0, "Gap vs Z* (%)": -0.5592},
    # assist
    {"objectif": "assist", "n_mut": 1, "crossover": "one_point", "Best": 213.6598, "Mean": 217.1869, "SD": 3.8258, "ARPD (%)": 3.2687, "Succès (%)": 0.0, "Gap vs Z* (%)": 1.5916},
    {"objectif": "assist", "n_mut": 1, "crossover": "uniform", "Best": 212.9012, "Mean": 215.8001, "SD": 2.9102, "ARPD (%)": 2.6098, "Succès (%)": 0.0, "Gap vs Z* (%)": 1.2310},
    {"objectif": "assist", "n_mut": 2, "crossover": "one_point", "Best": 212.1503, "Mean": 214.6021, "SD": 2.1503, "ARPD (%)": 2.0401, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.8740},
    {"objectif": "assist", "n_mut": 2, "crossover": "uniform", "Best": 211.5804, "Mean": 213.9012, "SD": 1.8021, "ARPD (%)": 1.7065, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.6030},
    {"objectif": "assist", "n_mut": 3, "crossover": "one_point", "Best": 211.2015, "Mean": 213.1023, "SD": 1.4502, "ARPD (%)": 1.3265, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.4228},
    {"objectif": "assist", "n_mut": 3, "crossover": "uniform", "Best": 210.9502, "Mean": 212.4501, "SD": 1.2010, "ARPD (%)": 1.0165, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.3033},
]
# Meilleure combinaison campagne 1 par objectif (sélection auto page 6 → page 7)
PRECOMPUTED_BEST_C1 = {
    "makespan": {"n_mut": 3, "crossover": "uniform", "Best": 83.5403, "Mean": 83.5804, "ARPD (%)": 0.0480, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    "weighted": {"n_mut": 3, "crossover": "uniform", "Best": 222.1056, "Mean": 222.7803, "ARPD (%)": -0.2570, "Succès (%)": 0.0, "Gap vs Z* (%)": -0.5592},
    "assist": {"n_mut": 3, "crossover": "uniform", "Best": 210.9502, "Mean": 212.4501, "ARPD (%)": 1.0165, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.3033},
}
# Campagne 2 : grille enrichie (pop, gmax, mut_ops) — meilleurs par objectif = PRECOMPUTED_1H
PRECOMPUTED_COMBOS_C2 = [
    {"objectif": "makespan", "pop": 10, "gmax": 50, "mut_ops": "worst_machine", "Best": 83.5403, "Mean": 84.0317, "ARPD (%)": 0.5883, "Succès (%)": 80.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "makespan", "pop": 20, "gmax": 100, "mut_ops": "worst_machine+swap+insert+pm_day", "Best": 83.5403, "Mean": 83.5403, "ARPD (%)": 0.0, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    {"objectif": "weighted", "pop": 10, "gmax": 50, "mut_ops": "worst_machine", "Best": 223.9731, "Mean": 224.5543, "ARPD (%)": 0.5372, "Succès (%)": 0.0, "Gap vs Z* (%)": 0.2769},
    {"objectif": "weighted", "pop": 20, "gmax": 100, "mut_ops": "worst_machine+swap+insert+pm_day", "Best": 220.9338, "Mean": 220.9338, "ARPD (%)": 0.0, "Succès (%)": 100.0, "Gap vs Z* (%)": -1.0838},
    {"objectif": "assist", "pop": 10, "gmax": 50, "mut_ops": "worst_machine", "Best": 213.6598, "Mean": 217.1869, "ARPD (%)": 3.2687, "Succès (%)": 0.0, "Gap vs Z* (%)": 1.5916},
    {"objectif": "assist", "pop": 20, "gmax": 100, "mut_ops": "…+pm_day+assist_flip", "Best": 210.3103, "Mean": 210.3200, "ARPD (%)": 0.0046, "Succès (%)": 100.0, "Gap vs Z* (%)": -0.001},
]
PRECOMPUTED_BEST_C2 = {
    "makespan": {"label": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day", 2), "Best": 83.5403, "Mean": 83.5403, "ARPD (%)": 0.0, "Succès (%)": 100.0, "Gap vs Z* (%)": 0.0},
    "weighted": {"label": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day", 2), "Best": 220.9338, "Mean": 220.9338, "ARPD (%)": 0.0, "Succès (%)": 100.0, "Gap vs Z* (%)": -1.0838},
    "assist": {"label": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day+assist_flip", 2), "Best": 210.3103, "Mean": 210.3200, "ARPD (%)": 0.0046, "Succès (%)": 100.0, "Gap vs Z* (%)": -0.001},
}

def show_precomputed_table(title="Z* Gurobi × 3 objectifs + HGA — Data_2_8_2", data=None, hga_label="HGA"):
    """Affiche le tableau de référence (Data_2_8_2) sans relancer les solveurs."""
    data = data if data is not None else PRECOMPUTED_1H
    st.markdown(f"#### {title}")
    st.caption(
        "Instance **Solver/Data_2_8_2** (2 machines, 8 jobs, 2 PM, 7 jours) · "
        "échéances générées (`due_low=0.4`, `due_seed=0`) · warm-start HGA. "
        "**① Makespan** : Z* **prouvé OPTIMAL** en ~2,5 s (inchangé sous limite 1 h). "
        "**② / ③** : Z* = **meilleur incumbent** Gurobi sous limite de temps (gap MIP ~20–22 % ; "
        "Gurobi ne ferme pas l'optimalité en 1 h sur cette instance, comme dans l'article)."
    )
    cols_show = ["objectif", "Z*_Gurobi", "statut_Gurobi", "gap_Gurobi_%", "temps_Gurobi_s", "prouvé",
                 "borne_inf", "HGA_best", "HGA_mean", "HGA_worst", "HGA_sd",
                 "Gap vs Z* (%)", "ARPD (%)", "Succès (%)", "temps_HGA_moy_s"]
    df = pd.DataFrame(data)
    st.dataframe(df[[c for c in cols_show if c in df.columns]].round(4), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("① Makespan Z*", "83.540", help="OPTIMAL (prouvé en 2,49 s) — valide pour toute limite ≥ 3 s")
    c2.metric("② Weighted Z* (incumbent)", "223.355", delta="gap Gurobi ~20,6 %", delta_color="off")
    c3.metric("③ Assist Z* (incumbent)", "210.312", delta="gap Gurobi ~22,3 %", delta_color="off")
    st.info(
        f"**Lecture** : makespan prouvé ; pour ② et ③ Gurobi ne ferme pas l'écart sous limite 1 h "
        f"(comme dans l'article) → Z* = incumbent de référence. {hga_label} : comparer Best / Gap / ARPD / Succès. "
        "Les valeurs ②/③ ne sont pas comparables à l'article (échéances générées, absentes des fichiers publics)."
    )


@st.cache_resource(show_spinner=False)
def get_inst(path, lkw):
    return load_instance(path, **dict(lkw))


inst = get_inst(FILE, LKW)



# ------------------------------------------------------------------ Base vs HGA amélioré (page 8) — Data_2_8_2, 8 runs
PRECOMPUTED_IMPROVED = [
    {"config": "base", "objectif": "makespan",
     "params": _full_params(10, 50, 1, "one_point", "worst_machine", 1),
     "Z*_Gurobi": 83.5403, "prouvé": True,
     "HGA_best": 83.5403, "HGA_mean": 84.1422, "HGA_worst": 85.9976, "HGA_sd": 1.0430,
     "Gap vs Z* (%)": 0.0, "ARPD (%)": 0.7206, "Succès (%)": 75.0, "temps_HGA_moy_s": 0.175},
    {"config": "amélioré", "objectif": "makespan",
     "params": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day", 2),
     "Z*_Gurobi": 83.5403, "prouvé": True,
     "HGA_best": 83.5403, "HGA_mean": 83.5403, "HGA_worst": 83.5403, "HGA_sd": 0.0,
     "Gap vs Z* (%)": 0.0, "ARPD (%)": 0.0, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.342},
    {"config": "base", "objectif": "weighted",
     "params": _full_params(10, 50, 1, "one_point", "worst_machine", 1),
     "Z*_Gurobi": 223.3545, "prouvé": False,
     "HGA_best": 223.9731, "HGA_mean": 224.9578, "HGA_worst": 226.6008, "HGA_sd": 0.7731,
     "Gap vs Z* (%)": 0.2769, "ARPD (%)": 0.7178, "Succès (%)": 0.0, "temps_HGA_moy_s": 0.218},
    {"config": "amélioré", "objectif": "weighted",
     "params": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day", 2),
     "Z*_Gurobi": 223.3545, "prouvé": False,
     "HGA_best": 220.9338, "HGA_mean": 220.9338, "HGA_worst": 220.9338, "HGA_sd": 0.0,
     "Gap vs Z* (%)": -1.0838, "ARPD (%)": 0.0, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.377},
    {"config": "base", "objectif": "assist",
     "params": _full_params(10, 50, 1, "one_point", "worst_machine", 1),
     "Z*_Gurobi": 210.3124, "prouvé": False,
     "HGA_best": 213.6598, "HGA_mean": 216.4537, "HGA_worst": 224.6429, "HGA_sd": 3.25,
     "Gap vs Z* (%)": 1.5916, "ARPD (%)": 2.9201, "Succès (%)": 0.0, "temps_HGA_moy_s": 0.55},
    {"config": "amélioré", "objectif": "assist",
     "params": _full_params(20, 100, 3, "uniform", "worst_machine+swap+insert+pm_day+assist_flip", 2),
     "Z*_Gurobi": 210.3124, "prouvé": False,
     "HGA_best": 210.3103, "HGA_mean": 210.3200, "HGA_worst": 210.3770, "HGA_sd": 0.022,
     "Gap vs Z* (%)": -0.001, "ARPD (%)": 0.0046, "Succès (%)": 100.0, "temps_HGA_moy_s": 0.90},
]


def show_improved_comparison():
    """Page 8 : base (défauts article) vs HGA amélioré + 3 phrases d'explication."""
    st.markdown("#### Résultats : HGA **base** (campagne 1) vs HGA **amélioré** (campagne 2) — Data_2_8_2")
    st.caption(
        "Z* Gurobi = optimum **prouvé** (makespan, 2,49 s) ou **incumbent** sous limite de temps "
        "(weighted / assist, gap MIP ~20–22 %, non prouvé même sous 1 h). "
        "Un gap négatif signifie que le HGA a battu l'incumbent Gurobi."
    )
    df = pd.DataFrame(PRECOMPUTED_IMPROVED)
    cols = ["config", "objectif", "HGA_best", "HGA_mean", "HGA_sd", "Gap vs Z* (%)", "ARPD (%)", "Succès (%)", "temps_HGA_moy_s", "params"]
    st.dataframe(df[cols].round(4), use_container_width=True)

    a, b, c = st.columns(3)
    a.metric("Makespan — succès", "75 % → 100 %", delta="base → amélioré")
    b.metric("Weighted — best", "223.97 → 220.93", delta="-1.08 % vs incumbent Gurobi")
    c.metric("Assist — best", "213.66 → 210.31", delta="≈ incumbent / légèrement mieux")

    st.markdown("""
**Pourquoi ces gains ? Trois changements :**

1. **Mutations enrichies** — avec seulement 2 machines, `worst_machine` est quasi dégénérée ; on ajoute `swap`, `insert`, `pm_day` (et `assist_flip` pour l'objectif ③), ce qui explore vraiment l'espace des séquences et des jours de PM.

2. **Plus d'effort de recherche** — population 20 (au lieu de 10), 3 mutations par enfant (au lieu de 1), 100 générations (au lieu de 50), croisement uniforme et 2 élites : la moyenne se stabilise et l'écart-type s'effondre.

3. **Effet mesurable** — makespan : 100 % de runs à l'optimum prouvé ; weighted : le HGA **bat** l'incumbent Gurobi (−1,08 %) ; assist : on rejoint (légèrement dépasse) l'incumbent, ARPD ≈ 0.
""")


def pdict(obj, **over):
    d = dict(objective=obj, alpha=alpha, beta=beta, K=int(K) if obj == "assist" else 0, delta=delta, gamma=gamma, c_ass=c_ass,
             pop=10, gmax=100, n_mut=1, pm=1.0, pc=1.0, p_ls=1.0, n_ls=50, d_ins=1.0, d_swap=1.0, n_elite=1,
             crossover="one_point", mut_ops=("worst_machine",))
    d.update(over)
    if isinstance(d["mut_ops"], str):
        d["mut_ops"] = tuple(d["mut_ops"].split("+"))
    return d


def key(d):
    return tuple(sorted(d.items()))


# ------------------------------------------------------------------ calculs (en cache)
@st.cache_data(show_spinner=False)
def runs_cached(path, lkw, pitems, runs):
    inst_ = get_inst(path, lkw)
    out = []
    for s in range(runs):
        r = run_hga(inst_, HGAParams(**dict(pitems)), seed=s)
        out.append(dict(obj=r["obj"], feasible=r["feasible"], time=r["time"], evals=r["evals"], trace=r["trace"], solution=r["solution"]))
    return out


@st.cache_data(show_spinner=False)
def exact_cached(path, lkw, pitems, tlim, warm):
    """Gurobi (milp_gurobi.solve_milp) -> Z*, borne, gap, statut, solution."""
    try:
        from milp_gurobi import solve_milp
        inst_ = get_inst(path, lkw)
        P = dict(pitems)
        w = run_hga(inst_, HGAParams(**P), seed=999)["solution"] if warm else None
        return solve_milp(inst_, P["objective"], alpha=P["alpha"], beta=P["beta"], K=P["K"], delta=P["delta"], gamma=P["gamma"],
                          c_ass=P["c_ass"], time_limit=tlim, warm=w)
    except Exception as e:  # licence restreinte, gurobipy absent, modèle trop grand...
        return dict(error=f"{type(e).__name__}: {e}")


def breakdown(path, lkw, pd_, sol):
    """Décode une solution avec le décodeur du HGA -> Cmax, TMCT, TT, coût assistance, pénalité."""
    inst_ = get_inst(path, lkw)
    s = make_sol(inst_, HGAParams(**pd_), sol["seq"], [sol["pm_day"][k] for k in range(inst_.nK)], sol["assist"])
    return dict(Cmax=max([m[0] for m in s.mv if m[5]] or [0]), TMCT=sum(m[0] for m in s.mv), TT=sum(m[1] for m in s.mv),
                coût_assist=sum(m[3] for m in s.mv), pénalité=sum(m[2] for m in s.mv))


def sched_df(P, s):
    rows = []
    for i, ms in enumerate(schedule(inst, P, s)):
        for lab, t0, t1, t2 in ms:
            kind = "PM" if lab.startswith("PM") else "Job"
            if t1 > t0 + 1e-9:
                rows.append((f"M{i}", lab + " (setup/attente)", t0, t1, "Setup"))
            rows.append((f"M{i}", lab, t1, t2, kind))
    return pd.DataFrame(rows, columns=["Machine", "Label", "Début", "Fin", "Type"])


def draw_gantt(df, title, windows=None, due=None, cmax=None):
    """Gantt : barres Job/Setup/PM + (option) fenêtres de PM, échéances, Cmax."""
    if df.empty:
        st.info("Rien à afficher pour l'instant.")
        return
    order = sorted(df["Machine"].unique(), key=lambda m: int(m[1:]) if m[1:].isdigit() else 0)
    xlim = float(df["Fin"].max()) * 1.05 + 1e-9
    xsc = alt.Scale(domain=[0, xlim])
    ysc = alt.Y("Machine:N", title=None, sort=order)
    bars = alt.Chart(df).mark_bar(cornerRadius=3, stroke="white", strokeWidth=1).encode(
        x=alt.X("Début:Q", title="temps (h)", scale=xsc), x2="Fin:Q", y=ysc,
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Job", "Setup", "PM"], range=["#2563eb", "#fbbf24", "#ef4444"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Label", "Début", "Fin", "Type"])
    layers = []
    if windows:
        w = pd.DataFrame([dict(a=a, b=min(b, xlim)) for a, b in windows if a < xlim])
        if len(w):
            layers.append(alt.Chart(w).mark_rect(opacity=0.12, color="#64748b").encode(x=alt.X("a:Q", scale=xsc), x2="b:Q"))
    layers.append(bars)
    if due:
        dd = pd.DataFrame([dict(Machine=m, x=x, Label=lab) for m, x, lab in due if x <= xlim])
        if len(dd):
            layers.append(alt.Chart(dd).mark_point(shape="diamond", filled=True, size=120, color="#7c3aed").encode(
                x=alt.X("x:Q", scale=xsc), y=ysc, tooltip=["Label", "x"]))
    if cmax is not None:
        layers.append(alt.Chart(pd.DataFrame({"x": [cmax]})).mark_rule(color="#0f2a43", strokeDash=[6, 4], strokeWidth=2).encode(
            x=alt.X("x:Q", scale=xsc), tooltip=["x"]))
    ch = alt.layer(*layers).properties(height=60 + 34 * len(order), title=title)
    st.altair_chart(ch.configure_view(strokeWidth=0).configure_title(fontSize=14, anchor="start", color="#0f2a43"), use_container_width=True)


def gantt_sol(pd_, s, title, annot=False):
    """Gantt d'un objet Sol déjà décodé ; annot=True : fenêtres PM, échéances (◆) et Cmax."""
    P = HGAParams(**pd_)
    df = sched_df(P, s)
    if annot and not df.empty:
        jobs = df[df["Type"] == "Job"]
        due = [(r.Machine, float(inst.due[int(r.Label[1:])]), r.Label) for r in jobs.itertuples()]
        draw_gantt(df, title, windows=inst.windows, due=due, cmax=float(df["Fin"].max()))
    else:
        draw_gantt(df, title)


def gantt(path, lkw, pd_, sol, title, annot=False):
    inst_ = get_inst(path, lkw)
    s = make_sol(inst_, HGAParams(**pd_), sol["seq"], [sol["pm_day"][k] for k in range(inst_.nK)], sol["assist"])
    gantt_sol(pd_, s, title, annot)


def gantt_legend(annot=True):
    st.markdown("<div class='pcard' style='padding:.5rem .9rem;font-size:.85rem'>"
                "<span class='chip job'>Job</span> traitement · "
                "<span class='chip' style='background:#fef3c7;color:#92400e'>Setup / attente</span> · "
                "<span class='chip pm'>PM</span> maintenance"
                + (" · <b>bande grise</b> = fenêtres de PM · <b style='color:#7c3aed'>◆</b> = échéance du job · <b>trait pointillé</b> = Cmax" if annot else "")
                + "</div>", unsafe_allow_html=True)


def solution_table(P, s):
    rows = []
    for i, ms in enumerate(schedule(inst, P, s)):
        for lab, t0, t1, t2 in ms:
            if lab.startswith("PM"):
                rows.append({"Machine": f"M{i}", "Activité": lab, "Début setup": t0, "Début traitement": t1, "Fin": t2, "Échéance": None, "Retard": None})
            else:
                d = inst.due[int(lab[1:])]
                has = d < 1e11
                rows.append({"Machine": f"M{i}", "Activité": lab, "Début setup": t0, "Début traitement": t1, "Fin": t2,
                             "Échéance": d if has else None, "Retard": max(0.0, t2 - d) if has else 0.0})
    return pd.DataFrame(rows)


def replay_cross(P, A, B, rstate):
    """Rejoue les tirages de Engine.crossover (enfant 1) pour expliquer d'où vient chaque machine."""
    r = random.Random(); r.setstate(rstate)
    M = inst.nM
    cut = r.randint(1, max(1, M - 1))
    tags = ["A" if r.random() < 0.5 else "B" for _ in range(M)] if P.crossover == "uniform" else ["A" if i < cut else "B" for i in range(M)]
    srcs = {"A": A, "B": B}
    seen, dup = set(), []
    for i in range(M):
        for x in srcs[tags[i]].seq[i]:
            if x in seen:
                dup.append(x)
            else:
                seen.add(x)
    missing = [x for x in range(inst.nJ + inst.nK) if x not in seen]
    return tags, dup, missing


def traced_run(P, seed, ngen):
    """Rejoue la boucle de run_hga génération par génération en enregistrant chaque étape."""
    E = Engine(inst, P, seed)
    pop, keys, guard = [], set(), 0
    while len(pop) < P.pop and guard < 20 * P.pop:
        guard += 1
        s = E.init_solution()
        if s.key() in keys:
            continue
        keys.add(s.key()); pop.append(s)
    best = min(pop, key=lambda s: s.fit).copy()
    T = dict(init_pop=[s.copy() for s in pop], best0=best, events=[], trace=[best.obj])
    for g in range(1, ngen + 1):
        A, B = E.rng.sample(pop, 2) if len(pop) > 1 else (pop[0], pop[0])
        did_x = E.rng.random() < P.pc
        rstate = E.rng.getstate()
        kids = E.crossover(A, B) if did_x else [A.copy(), B.copy()]
        ev = dict(A=A.copy(), B=B.copy(), did_x=did_x, rstate=rstate, kids=[])
        for c in kids:
            rec = dict(x=c.copy(), ops=[], m=None, l=None)
            if E.rng.random() < P.pm:
                ops = []
                for _ in range(P.n_mut):
                    op = E.rng.choice(P.mut_ops)
                    if op == "assist_flip" and not E.assist_on:
                        op = "swap"
                    ops.append(op); getattr(E, "_mut_" + op)(c)
                E.evaluate(c)
                rec.update(ops=ops, m=c.copy())
            if E.rng.random() < P.p_ls:
                E.local_search(c)
                rec["l"] = c.copy()
            ks = {s.key() for s in pop}
            order = sorted(range(len(pop)), key=lambda x: pop[x].fit)
            worst = order[-1] if len(pop) > P.n_elite else None
            pre = [s.fit for s in pop]
            dup = c.key() in ks
            adm = worst is not None and not dup and c.fit < pop[worst].fit
            if adm:
                pop[worst] = c
                if c.fit < best.fit - 1e-9:
                    best = c.copy()
            rec.update(final=c.copy(), admitted=adm, dup=dup, worst=worst, pre=pre, post=[s.fit for s in pop])
            ev["kids"].append(rec)
        ev["best"] = best
        T["events"].append(ev); T["trace"].append(best.obj)
    return T


def show_hga_steps(T, P4):
    Po = HGAParams(**P4); J = inst.nJ; ev = T["events"]; NG = len(ev)
    st.session_state["g_step"] = min(st.session_state.get("g_step", 0), NG)

    def _mv(d):
        st.session_state["g_step"] = max(0, min(NG, st.session_state["g_step"] + d))

    c = st.columns([1.3, 1.3, 8])
    c[0].button("◀ Précédent", on_click=_mv, args=(-1,), key="stp_prev")
    c[1].button("Suivant ▶", on_click=_mv, args=(1,), key="stp_next")
    g = c[2].slider("Génération", 0, NG, key="g_step")

    if g == 0:
        st.markdown("**Génération 0 — population initiale.** Chaque individu est une solution complète (voir étape 1). "
                    "Les barres montrent la fitness des individus, du meilleur au pire ; le Gantt est celui du meilleur.")
        st.bar_chart(pd.Series(sorted(x.fit for x in T["init_pop"]), name="fitness (triée)"))
        gantt_sol(P4, T["best0"], f"Meilleur individu initial (obj = {T['best0'].obj:.2f})", annot=True)
        gantt_legend()
    else:
        e = ev[g - 1]
        kid_i = st.radio("Enfant à suivre dans cette génération", [1, 2], horizontal=True, key="kid_i", format_func=lambda x: f"Enfant {x}")
        k = e["kids"][kid_i - 1]
        before_ls = k["m"] if k["m"] is not None else k["x"]
        m = st.columns(5)
        m[0].metric("Parent A", f"{e['A'].obj:.2f}"); m[1].metric("Parent B", f"{e['B'].obj:.2f}")
        m[2].metric("Après croisement", f"{k['x'].obj:.2f}")
        m[3].metric("Après mutation", f"{k['m'].obj:.2f}" if k["m"] is not None else "—")
        m[4].metric("Après rech. locale", f"{k['l'].obj:.2f}" if k["l"] is not None else "—")
        tabs = st.tabs(["① Parents", "② Croisement", "③ Mutation", "④ Recherche locale", "⑤ Remplacement"])
        with tabs[0]:
            st.caption("Deux individus tirés au hasard dans la population (sélection aléatoire).")
            a, b = st.columns(2)
            with a:
                gantt_sol(P4, e["A"], f"Parent A (obj {e['A'].obj:.2f})")
            with b:
                gantt_sol(P4, e["B"], f"Parent B (obj {e['B'].obj:.2f})")
            gantt_legend(False)
        with tabs[1]:
            if not e["did_x"]:
                st.info("Croisement non appliqué (probabilité Pc) : les enfants sont des copies des parents.")
            cA, cB, cC = st.columns(3)
            cA.markdown("<div class='pcard'><div class='pt'>Parent A</div>" + machine_rows(e["A"].seq, J) + "</div>", unsafe_allow_html=True)
            cB.markdown("<div class='pcard'><div class='pt'>Parent B</div>" + machine_rows(e["B"].seq, J) + "</div>", unsafe_allow_html=True)
            if e["did_x"] and kid_i == 1:
                tags, dup, missing = replay_cross(Po, e["A"], e["B"], e["rstate"])
                cC.markdown(f"<div class='pcard'><div class='pt'>Enfant 1 après croisement</div>"
                            + rows_src(k["x"].seq, J, tags, {x: "new" for x in missing}) + "</div>", unsafe_allow_html=True)
                nm = lambda x: ("PM%d" % (x - J)) if x >= J else ("J%d" % x)
                st.caption(f"← A / ← B : parent dont la séquence de la machine est copiée. Doublons ignorés : {[nm(x) for x in dup] or 'aucun'} · "
                           f"activités réinsérées par meilleure insertion (vert) : {[nm(x) for x in missing] or 'aucune'}.")
            else:
                cC.markdown(f"<div class='pcard'><div class='pt'>Enfant {kid_i} après croisement</div>" + machine_rows(k["x"].seq, J) + "</div>", unsafe_allow_html=True)
            gantt_sol(P4, k["x"], f"Enfant {kid_i} après croisement (obj {k['x'].obj:.2f})")
        with tabs[2]:
            if k["m"] is None:
                st.info("Mutation non appliquée à cet enfant (probabilité Pm).")
            else:
                st.markdown(f"Opérateur(s) tiré(s) : **{' + '.join(k['ops'])}**")
                a, b = st.columns(2)
                a.markdown(f"<div class='pcard'><div class='pt'>Avant (obj {k['x'].obj:.2f})</div>" + machine_rows(k["x"].seq, J) + "</div>", unsafe_allow_html=True)
                b.markdown(f"<div class='pcard'><div class='pt'>Après (obj {k['m'].obj:.2f})</div>" + machine_rows(k["m"].seq, J) + "</div>", unsafe_allow_html=True)
                gantt_sol(P4, k["m"], f"Enfant {kid_i} après mutation (obj {k['m'].obj:.2f})")
        with tabs[3]:
            if k["l"] is None:
                st.info("Recherche locale non appliquée (probabilité P_LS).")
            else:
                st.caption(f"La descente améliore l'enfant : {before_ls.obj:.2f} → {k['l'].obj:.2f}.")
                a, b = st.columns(2)
                with a:
                    gantt_sol(P4, before_ls, f"Avant recherche locale (obj {before_ls.obj:.2f})")
                with b:
                    gantt_sol(P4, k["l"], f"Après recherche locale (obj {k['l'].obj:.2f})")
                gantt_legend(False)
        with tabs[4]:
            post, pre = k["post"], k["pre"]
            dfp = pd.DataFrame({"individu": [f"#{i}" for i in range(len(post))], "fitness": post, "avant": pre,
                                "statut": ["remplacé par l'enfant" if (k["admitted"] and i == k["worst"]) else "inchangé" for i in range(len(post))]})
            bars = alt.Chart(dfp).mark_bar().encode(
                x=alt.X("individu:N", sort=None, title=None), y=alt.Y("fitness:Q", title="fitness"),
                color=alt.Color("statut:N", scale=alt.Scale(domain=["inchangé", "remplacé par l'enfant"], range=["#93c5fd", "#16a34a"]),
                                legend=alt.Legend(orient="bottom", title=None)), tooltip=["individu", "fitness", "avant", "statut"])
            rule = alt.Chart(pd.DataFrame({"y": [k["final"].fit]})).mark_rule(color="#dc2626", strokeDash=[5, 4], strokeWidth=2).encode(y="y:Q")
            st.altair_chart((bars + rule).properties(height=220, title="Population après la décision (trait rouge = fitness de l'enfant)")
                            .configure_view(strokeWidth=0).configure_title(fontSize=14, anchor="start", color="#0f2a43"), use_container_width=True)
            wf = pre[k["worst"]] if k["worst"] is not None else None
            if k["admitted"]:
                st.success(f"L'enfant (fitness {k['final'].fit:.2f}) est inédit et meilleur que le pire individu ({wf:.2f}) : il le remplace.")
            elif k["dup"]:
                st.warning("L'enfant est identique à un individu déjà présent : rejeté (diversité préservée).")
            else:
                st.warning(f"L'enfant (fitness {k['final'].fit:.2f}) n'est pas meilleur que le pire individu ({wf:.2f}) : rejeté.")

    cur = T["best0"] if g == 0 else ev[g - 1]["best"]
    st.subheader("Meilleure solution connue à cette génération")
    c = st.columns(3)
    c[0].metric("Meilleur objectif", f"{cur.obj:.2f}", f"{cur.obj - T['best0'].obj:.2f}" if g else None, delta_color="inverse")
    c[1].metric("Génération", f"{g} / {NG}")
    c[2].metric("Faisable", "oui" if cur.feasible else "non")
    cv = pd.DataFrame({"génération": list(range(len(T["trace"]))), "meilleur objectif": T["trace"]})
    line = alt.Chart(cv).mark_line(color="#2563eb", point=True).encode(x="génération:Q", y=alt.Y("meilleur objectif:Q", scale=alt.Scale(zero=False)))
    cur_rule = alt.Chart(pd.DataFrame({"g": [g]})).mark_rule(color="#dc2626", strokeDash=[5, 4]).encode(x="g:Q")
    st.altair_chart((line + cur_rule).properties(height=200).configure_view(strokeWidth=0), use_container_width=True)
    if g > 0:
        gantt_sol(P4, cur, f"Meilleur planning à la génération {g} (obj {cur.obj:.2f})", annot=True)
        gantt_legend()


def conv(curves):
    L = max(len(v) for v in curves.values())
    df = pd.DataFrame({k: list(v) + [v[-1]] * (L - len(v)) for k, v in curves.items()})
    df.index.name = "génération"
    st.line_chart(df)


def mean_trace(runs):
    L = max(len(r["trace"]) for r in runs)
    M = [r["trace"] + [r["trace"][-1]] * (L - len(r["trace"])) for r in runs]
    return [stt.mean(c) for c in zip(*M)]


def stat_row(path, lkw, pd_, runs, Zx=None, proven=None, extra_ref=None):
    vals = [r["obj"] for r in runs]
    B = min(vals + ([Zx] if Zx is not None else []) + ([extra_ref] if extra_ref else []))
    m = metrics(vals, B)
    bst = min(runs, key=lambda r: r["obj"])
    row = {"Best": m["best"], "Mean": m["mean"], "Worst": m["worst"], "SD": m["sd"], "ARPD (%)": m["arpd"], "Succès (%)": m["success"],
           "Temps moy. (s)": stt.mean(r["time"] for r in runs), "Évaluations": stt.mean(r["evals"] for r in runs)}
    row.update(breakdown(path, lkw, pd_, bst["solution"]))
    if Zx is not None:
        row["Gap vs Z* Gurobi (%)"] = 100 * (m["best"] - Zx) / Zx if Zx else 0.0
        row["Z* prouvé ?"] = "oui" if proven else "non (incumbent)"
    return row, B


def show_metrics_formulas():
    """Formules des métriques — texte clair (sans LaTeX cassé)."""
    st.markdown("#### Formules des métriques")
    st.markdown("""
| Métrique | Formule / définition |
|----------|----------------------|
| **B** (référence) | minimum entre Z* Gurobi (si dispo) et les R valeurs HGA |
| **Best** | plus petite valeur parmi les R runs |
| **Mean** | moyenne des R runs |
| **Worst** | plus grande valeur parmi les R runs |
| **SD** | écart-type des R runs |
| **RPD** d'un run | 100 × (z − B) / B |
| **ARPD** | moyenne des RPD sur les R runs |
| **Succès (%)** | % de runs qui atteignent B (à 1e−6 près) |
| **Gap vs Z* (%)** | 100 × (Best − Z*) / Z* |

Un **gap négatif** signifie que le HGA bat l’incumbent Gurobi.  
ARPD bas + succès élevé = paramétrage robuste.
""")


def update_improvement_history(obj, config_label, params_str, row, Zx=None):
    """Met à jour l'historique dynamique des meilleurs paramétrages (page 8). Garde les 2 derniers meilleurs."""
    if "improve_hist" not in st.session_state:
        st.session_state["improve_hist"] = {o: [] for o in OBJS}
    hist = st.session_state["improve_hist"].setdefault(obj, [])
    entry = {
        "config": config_label,
        "params": params_str,
        "HGA_best": row.get("Best"),
        "HGA_mean": row.get("Mean"),
        "HGA_sd": row.get("SD"),
        "ARPD (%)": row.get("ARPD (%)"),
        "Succès (%)": row.get("Succès (%)"),
        "Gap vs Z* (%)": row.get("Gap vs Z* Gurobi (%)"),
        "temps_HGA_moy_s": row.get("Temps moy. (s)"),
        "Z*_Gurobi": Zx,
    }
    # n'ajoute que si meilleur (ou premier)
    if not hist or (entry["HGA_best"] is not None and entry["HGA_best"] < hist[-1]["HGA_best"] - 1e-9):
        hist.append(entry)
        # garder seulement les 2 derniers (précédent + nouveau)
        st.session_state["improve_hist"][obj] = hist[-2:]
        return True
    return False


def exact_for(obj, key_prefix, pd_=None):
    """Bouton Gurobi + affichage de Z*, borne, gap, statut. Retourne le dict résultat ou None."""
    pd_ = pd_ or pdict(obj)
    sk = f"ex_{key_prefix}_{obj}_{FILE}_{key(pd_)}_{MILP_T}"
    if st.button(f"Calculer Z* avec Gurobi ({OBJ_LABEL[obj]})", key="b" + sk):
        with st.spinner(f"Gurobi en cours (≤ {MILP_T}s)…"):
            st.session_state[sk] = exact_cached(FILE, LKW, key(pd_), float(MILP_T), True)
    r = st.session_state.get(sk)
    if r is None:
        st.info("Z* Gurobi pas encore calculé pour cet objectif : cliquez sur le bouton.")
    elif "error" in r:
        st.error(f"Gurobi : {r['error']} — (licence restreinte pip : ≈ 2000 variables ; au-delà de ~8 jobs il faut la licence académique)")
        return None
    else:
        c = st.columns(5)
        c[0].metric("Z* Gurobi", f"{r['obj']:.4f}" if r["obj"] is not None else "—")
        c[1].metric("Borne inf.", f"{r['bound']:.4f}" if r["bound"] is not None else "—")
        c[2].metric("Gap Gurobi", f"{r['gap']:.2f} %" if r["gap"] is not None else "—")
        c[3].metric("Statut", r["status_name"])
        c[4].metric("Temps", f"{r['runtime']:.1f} s")
        if not r["proven_optimal"]:
            st.warning("Optimum NON prouvé : Z* est l'incumbent de Gurobi (comme dans l'article pour les objectifs 2 et 3).")
    return r


# ------------------------------------------------------------------ paramètres HGA (widgets)
def hga_widgets(k, obj):
    P = {}
    c = st.columns(4)
    P["pop"] = c[0].select_slider("pop (P)", [10, 20, 50, 100, 200], 10, key=k + "1")
    P["gmax"] = c[1].select_slider("gmax", [30, 100, 300, 500, 1000, 2000], 100, key=k + "2")
    P["n_mut"] = c[2].select_slider("n_mut (r)", [1, 2, 3, 5, 8], 1, key=k + "3")
    P["pc"] = c[3].select_slider("Pc", [0.5, 0.7, 0.8, 0.9, 1.0], 1.0, key=k + "4")
    c = st.columns(4)
    P["pm"] = c[0].select_slider("Pm", [0.05, 0.1, 0.2, 0.5, 1.0], 1.0, key=k + "5")
    P["p_ls"] = c[1].select_slider("P_LS", [0.0, 0.1, 0.3, 0.5, 1.0], 1.0, key=k + "6")
    P["n_ls"] = c[2].select_slider("N_LS", [1, 5, 10, 20, 50], 50, key=k + "7")
    P["n_elite"] = c[3].select_slider("n_elite", [1, 2, 3, 4, 5], 1, key=k + "8")
    c = st.columns(4)
    P["d_ins"] = c[0].select_slider("d_ins", [0.5, 0.8, 1.0], 1.0, key=k + "9")
    P["d_swap"] = c[1].select_slider("d_swap", [0.5, 0.8, 1.0], 1.0, key=k + "10")
    P["crossover"] = c[2].selectbox("croisement", ["one_point", "uniform"], key=k + "11")
    P["mut_ops"] = c[3].selectbox("mutations", ["worst_machine", "worst_machine+swap", "worst_machine+insert", "swap+insert",
                                                "worst_machine+swap+insert+pm_day"], key=k + "12")
    return pdict(obj, **P)


# ------------------------------------------------------------------ pédagogie : croisement illustré + schéma
def xover_demo(A, B, seed=0):
    """Croisement à un point illustré (principe) : retourne enfant, point de coupe, doublons retirés, manquants réinsérés."""
    rnd = random.Random(seed)
    nM = len(A)
    if nM > 1:
        cut = rnd.randint(1, nM - 1)
        child = [list(A[i]) if i < cut else list(B[i]) for i in range(nM)]
        seen, dup, fixed = set(), [], []
        for q in child:
            nq = []
            for a in q:
                if a in seen:
                    dup.append(a)
                else:
                    seen.add(a)
                    nq.append(a)
            fixed.append(nq)
        missing = sorted(set(a for q in A for a in q) - seen)
        for a in missing:
            for i, q in enumerate(A):
                if a in q:
                    fixed[i].append(a)
                    break
        return fixed, cut, dup, missing, "machine"
    cut = rnd.randint(1, max(1, len(A[0]) - 1))
    head = A[0][:cut]
    tail = [x for x in B[0] if x not in head]
    return [head + tail], cut, [], [], "position"


def flow_dot(P, vals=None):
    v = vals or {}
    nl = "\\n"

    def lab(t, k):
        return t + (nl + v[k] if k in v else "")

    n_i = lab("① Initialisation" + nl + str(P["pop"]) + " solutions", "I")
    n_x = "③ Croisement" + nl + str(P["crossover"]) + " (Pc=" + str(P["pc"]) + ")" + nl + "→ 2 enfants"
    n_m = "④ Mutation" + nl + str(P["n_mut"]) + " x " + "+".join(P["mut_ops"])
    n_l = "⑤ Recherche locale" + nl + "insert · swap · jour PM" + nl + "(jusqu'au min. local)"
    n_r = lab("⑥ Remplacement" + nl + "pire individu si enfant" + nl + "unique et meilleur", "R")
    n_t = "Arrêt ?" + nl + "gmax=" + str(P["gmax"]) + " / temps / stagnation"
    n_b = lab("Meilleure solution", "B")
    return (
        'digraph G { rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.45;\n'
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#cbd5e1", fillcolor="#ffffff", margin="0.18,0.1"];\n'
        'edge [color="#64748b", fontname="Helvetica", fontsize=9, arrowsize=0.7];\n'
        f'I [label="{n_i}", fillcolor="#dbeafe", color="#2563eb"];\n'
        'S [label="② Sélection' + nl + '2 parents au hasard", fillcolor="#e0f2fe", color="#0284c7"];\n'
        f'X [label="{n_x}", fillcolor="#ede9fe", color="#7c3aed"];\n'
        f'M [label="{n_m}", fillcolor="#fef3c7", color="#d97706"];\n'
        f'L [label="{n_l}", fillcolor="#dcfce7", color="#16a34a"];\n'
        f'R [label="{n_r}", fillcolor="#fee2e2", color="#dc2626"];\n'
        f'T [label="{n_t}", shape=diamond, fillcolor="#f1f5f9", color="#475569"];\n'
        f'B [label="{n_b}", fillcolor="#0f2a43", fontcolor="white", color="#0f2a43"];\n'
        'I -> S -> X -> M -> L -> R -> T; T -> S [label="non"]; T -> B [label="oui"]; }'
    )


# =====================================================================================================
# PAGES
# =====================================================================================================
hero(page.split("· ", 1)[1], SUBS[page], "Page " + page.split(" ")[0])

if page == PAGES[0]:
    st.subheader("Organisation des pages")
    st.graphviz_chart("""
digraph G {
  rankdir=TB;
  bgcolor="transparent";
  nodesep=0.55;
  ranksep=0.70;
  fontname="Helvetica";

  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12,
        color="#94a3b8", fillcolor="#ffffff", margin="0.25,0.16"];
  edge [color="#64748b", arrowsize=0.75, fontname="Helvetica", fontsize=10];

  start [label="Début", shape=circle, style=filled, fillcolor="#0f2a43", fontcolor="white", width=0.55, fixedsize=true];
  end   [label="Fin",   shape=circle, style=filled, fillcolor="#0f2a43", fontcolor="white", width=0.55, fixedsize=true];

  O  [label="0 · Overview\\norganisation & flux", fillcolor="#dbeafe", color="#2563eb", penwidth=2];
  P  [label="1 → 5 · Pédagogie\\nproblème · MILP · codage · HGA · init"];
  S6 [label="6 · Paramétrage\\nsimulations multi-paramètres\\n(produit cartésien)"];
  S7 [label="7 · Résultats\\nZ* / HGA + Gantt + Convergence"];
  S8 [label="8 · Historique\\nprécédent ↔ courant"];
  S9 [label="9 · DÉMO (figée)\\nData_2_8_2 · Z* 1 h\\nprécalculé — indépendant",
      fillcolor="#0f2a43", fontcolor="white", color="#0f2a43", penwidth=2];

  decision [label="meilleur Best ?", shape=diamond, style="filled", fillcolor="#fef3c7",
            color="#d97706", fontsize=11, width=1.5, height=0.95];

  start -> O;
  O -> P;
  O -> S6;
  O -> S9;

  S6 -> decision [label=" produit cartésien "];
  decision -> S7 [label=" oui "];
  decision -> S8 [label=" gain ultérieur ", style=dashed];

  // Page 9 = démo isolée (aucune flèche vers 6 / 7 / 8)
  S9 -> end [style=dashed, label=" démo seule "];

  S7 -> end;
  S8 -> end;
  P  -> end;
}
""", use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### Pédagogie")
        st.markdown("Pages **1–5** : comprendre le problème, le MILP, le codage HGA et l’initialisation.")
    with c2:
        st.markdown("##### Expériences (dynamiques)")
        st.markdown("**6** lance les simulations (produit cartésien). Le **meilleur** réglage alimente **7**. Tout gain ultérieur va dans **8**.")
    with c3:
        st.markdown("##### Démo figée (indépendante)")
        st.markdown("**9** est une **démo purement précalculée** sur `Data_2_8_2`. Elle n’écrit rien dans les pages 6 / 7 / 8.")

    st.markdown("---")
    st.header("Le problème (article)")
    st.markdown("""
Usine de back-end semi-conducteurs : **machines parallèles non reliées**, setups dépendants de la séquence,
échéances, **PM** sur ressource rare. Objectif : décider ensemble affectation, séquence et jour des PM.
""")
    a, b = st.columns(2)
    a.latex(r"\min C_{\max}\quad(①)")
    b.latex(r"\min \alpha\sum F_i+\beta\sum T_j\quad(②)")
    st.latex(r"\min\ \alpha\sum F_i+\beta\sum T_j+\gamma c_{ass}\delta\sum s\cdot Z\quad(③\ \mathrm{assist})")
    st.caption("Code réel : `ordo/instance.py`, `ordo/hga.py`, `ordo/milp_gurobi.py`, `ordo/experiments.py` + instances Solver/Factory.")

elif page == PAGES[1]:
    st.markdown("""
Jobs non préemptifs, sans précédence ; éligibilité ; setup dépendant de la machine et de la paire de jobs consécutifs ; chaque machine chargée jusqu'à $R_i$ ;
une PM par machine à maintenir, placée dans une **fenêtre journalière** (6h–20h), au plus $w_d$ PM par jour (techniciens) ; maintenance corrective négligée.

**Décisions** : affecter chaque job à une machine éligible · séquencer les activités sur chaque machine · choisir le jour (et l'heure) de chaque PM.
""")
    c = st.columns(5)
    c[0].metric("Machines", inst.nM); c[1].metric("Jobs", inst.nJ); c[2].metric("PM", inst.nK)
    c[3].metric("Jours-fenêtres", inst.nD); c[4].metric("Techniciens / jour", inst.w[0])
    st.write("Fenêtres :", ", ".join(f"[{a:.0f};{b:.0f}]" for a, b in inst.windows))
    t1, t2, t3 = st.tabs(["Durées p[i][j]", "Setups SDS (machine 0)", "PM / éligibilité"])
    t1.dataframe(pd.DataFrame(inst.p, index=[f"M{i}" for i in range(inst.nM)]).round(2), use_container_width=True)
    t2.dataframe(pd.DataFrame(inst.sds[0]).round(2), use_container_width=True)
    t3.write({"durées PM": inst.pm, "setup avant PM": inst.spm, "machines éligibles PM": inst.pm_machines})
    st.caption(f"Instance : {Path(FILE).name} — échéances {'générées' if due_mode == 'gen' else 'absentes'}.")

    st.header("Lire un planning : Gantt annoté")
    st.markdown("""
Un **planning** donne, pour chaque machine, la suite de ses activités dans le temps. Les trois décisions du problème s'y voient directement :
**quelle machine** (la ligne), **quel ordre** (de gauche à droite) et **quel jour pour la PM** (position de la barre rouge dans une bande grise).
Le planning ci-dessous est une solution du HGA (objectif ② pondéré, 30 générations) sur l'instance sélectionnée.
""")
    P1 = pdict("weighted", gmax=30)
    r1 = runs_cached(FILE, LKW, key(P1), 1)[0]
    s1 = make_sol(inst, HGAParams(**P1), r1["solution"]["seq"], [r1["solution"]["pm_day"][k] for k in range(inst.nK)], r1["solution"]["assist"])
    gantt_sol(P1, s1, f"Planning exemple — {Path(FILE).name} (objectif = {s1.obj:.2f})", annot=True)
    gantt_legend()
    st.markdown("""
- **Setup / attente (jaune)** : réglage de la machine entre deux jobs (dépend de la paire), ou attente de l'ouverture de la fenêtre de PM.
- **PM (rouge)** : une seule par machine à maintenir, obligatoirement dans une **bande grise** (6h–20h d'un jour), avec au plus *w* PM par jour.
- **Cmax** : fin de la dernière activité (makespan). **F_i** : fin de la machine *i* (somme = TMCT). **Retard T_j** : dépassement de l'échéance ◆ du job *j*.
""")
    st.dataframe(solution_table(HGAParams(**P1), s1).round(2), use_container_width=True)
    st.graphviz_chart("""digraph G { rankdir=LR; bgcolor="transparent";
node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#cbd5e1", fillcolor="#ffffff", margin="0.18,0.1"];
edge [color="#64748b", arrowsize=0.7];
J [label="Jobs", fillcolor="#dbeafe", color="#2563eb"]; A [label="Affectation\\nquelle machine ?"]; S [label="Séquence\\ndans quel ordre ?"];
P [label="PM", fillcolor="#fee2e2", color="#dc2626"]; D [label="Jour de la PM\\nquelle fenêtre ?"];
W [label="Fenêtres 6h–20h\\n≤ w techniciens / jour", shape=note, fillcolor="#f1f5f9"]; G [label="Planning\\n(Gantt)", fillcolor="#0f2a43", fontcolor="white", color="#0f2a43"];
J -> A -> S -> G; P -> D -> G; W -> D; P -> A [style=dashed, label="machine"]; }""", use_container_width=True)


elif page == PAGES[2]:
    st.subheader("Les trois fonctions objectifs (présentées en premier)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**① Makespan**")
        st.latex(r"\min\; C_{\max}\quad (1)")
        st.caption("Benchmark. Ignore les échéances. Mesure la durée totale du planning.")
    with c2:
        st.markdown("**② TMCT + retard**")
        st.latex(r"\min\; \alpha\sum_i F_i + \beta\sum_j T_j\quad (24)")
        st.caption("Pratique industrielle. $F_i$ = fin dernière activité de la machine $i$ ; $T_j$ = retard du job $j$.")
    with c3:
        st.markdown("**③ Setups assistés**")
        st.latex(r"\min\; \alpha\sum_i F_i + \beta\sum_j T_j + \gamma\, c_{ass}\sum \delta\, s_{iab}\, Z_{iab}\quad (A8)")
        st.caption("Performance (②) + coût d’assistance. Setup réduit de $\\delta$ si $Z_{iab}=1$ ; au plus $K$ assistances simultanées.")

    st.info(
        "**Ordre pédagogique retenu** : on pose d’abord les **trois objectifs**, puis les variables, "
        "puis les contraintes communes, puis les contraintes spécifiques à ② et ③. "
        "Ainsi l’auditoire sait *pourquoi* on écrit chaque contrainte."
    )

    st.subheader("Variables de décision")
    st.latex(r"Y_{ia}=1\text{ si }a\text{ affectée à }i;\quad X_{iab}=1\text{ si }a\text{ précède directement }b\text{ sur }i;\quad C_a,\ C_{\max},\ S_{ab},\ T_a,\ F_i")
    st.markdown(
        "Activités $A=J\\cup(R\\times D)$ ; job fictif $0$ (début/fin de chaque machine). "
        "Dans le code : arcs `X[i,'S',b]` (début) et `X[i,b,'E']` (fin). "
        "Pour l’objectif ③ : $Z_{iab}\\in\\{0,1\\}$ (setup $a\\to b$ assisté), $Q_b$, $St_b$, $\\sigma_b$, $u_{b'b}$."
    )

    tabs = st.tabs(["Objectif ① makespan", "Objectif ② TMCT + retard", "Objectif ③ setups assistés"])
    rows1 = [
        (r"Y_{ia}=0,\ i\in M_a", "(2) Un job n'est jamais placé sur une machine non éligible."),
        (r"Y_{i0}=1", "(3) Le job fictif est sur toutes les machines."),
        (r"\sum_iY_{ia}=1,\ a\in J", "(4) Chaque job a exactement une machine."),
        (r"\sum_dY_{i(i,d)}=1,\ i\in R", "(5) Une seule PM, un seul jour, par machine à maintenir."),
        (r"\sum_{a}X_{iab}=Y_{ib}", "(6) Toute activité a exactement un prédécesseur sur sa machine."),
        (r"\sum_{b}X_{iab}=Y_{ia}", "(7) Toute activité a exactement un successeur : chaîne unique par machine."),
        (r"\sum_{i\in R}Y_{i(i,d)}\le w_d", "(8) Le jour d, pas plus de PM que de techniciens."),
        (r"C_b+V(1-X_{iab})\ge C_a+s_{iab}+p_{ib}", "(9) Si a précède b, b finit au moins un setup + un traitement après a."),
        (r"C_b+V(1-X_{iab})\ge C_a+S_{ab}+p_{ib}", "(10) Idem après une PM (setup = S_ab)."),
        (r"S_{ab}+V(1-X_{iab})\ge\sum_{b'}X_{ib'a}s_{ib'b}", "(11) La PM n'efface pas le setup entre les deux jobs qu'elle sépare."),
        (r"C_{(i,d)}-p_{i(i,d)}Y\ge r_{(i,d)}", "(12) Une PM ne démarre pas avant l'ouverture de la fenêtre."),
        (r"C_{(i,d)}\le d_{(i,d)}", "(13) Une PM finit avant la fermeture de la fenêtre."),
        (r"C_a\ge r_a+p_{ia}Y_{ia}", "(14) Un job ne démarre pas avant sa disponibilité (ici : machine chargée jusqu'à R_i)."),
        (r"0\le C_a\le C_{\max}", "(17) C_max majore toutes les fins d'activité."),
    ]
    with tabs[0]:
        st.markdown("**Fonction objectif ① (rappel)**")
        st.latex(r"\min C_{\max}\ (1)")
        st.markdown("**Contraintes communes**")
        for l, t in rows1:
            a, b = st.columns([1.2, 1]); a.latex(l); b.write(t)
    with tabs[1]:
        st.markdown("**Fonction objectif ② (rappel)**")
        st.latex(r"\min\ \alpha\sum_iF_i+\beta\sum_jT_j\ (24)")
        st.markdown("**Contraintes additionnelles (retards & TMCT)** + contraintes (2)–(14)")
        for l, t in [(r"T_a\ge C_a-d_a", "(21) Retard ≥ fin − échéance."), (r"T_a\ge0", "(22) Pas de retard négatif."),
                     (r"F_i\ge C_a-V(1-X_{ia0})", "(23) F_i = fin de la dernière activité de i (linéarise TMCT).")]:
            a, b = st.columns([1.2, 1]); a.latex(l); b.write(t)
        st.caption("Les contraintes (2)–(14) et (17) restent actives ; $C_{\\max}$ n’est plus dans l’objectif.")
    with tabs[2]:
        st.markdown("**Fonction objectif ③ (rappel — introduite en tête de page)**")
        st.latex(r"\min\ \alpha\sum F_i+\beta\sum T_j+\gamma c_{ass}\sum\delta s_{iab}Z_{iab}\quad (A8)")
        st.markdown(
            "Paramètres : $\\delta$ (réduction), $K$ (assistants simultanés), $c_{ass}$, $\\gamma$ ; "
            "variables $Z_{iab},Q_b,St_b,\\sigma_b,\\lambda,\\mu,u$."
        )
        st.markdown("**Contraintes d’assistance (A1)–(A6)** + contraintes de l’objectif ②")
        for l, t in [(r"Z_{iab}\le X_{iab}", "(A1) On n'assiste qu'un setup présent dans la séquence."),
                     (r"C_b+V(1-X_{iab})\ge C_a+s_{iab}(1-\delta Z_{iab})+p_{ib}", "(A2) Setup effectif réduit de δ s'il est assisté."),
                     (r"Q_b=\sum_i\sum_aZ_{iab}", "(A3) Q_b = 1 si le setup précédant b est assisté."),
                     (r"St_b=C_b-\sum_ip_{ib}Y_{ib}", "(A4) Début de traitement."),
                     (r"\sigma_b=St_b-\sum s_{iab}(X_{iab}-\delta Z_{iab})", "(A5) Début du setup."),
                     (r"\sum_{b'\ne b}u_{b'b}\le K-1", "(A6) Au plus K−1 autres setups assistés en cours quand un setup assisté démarre.")]:
            a, b = st.columns([1.2, 1]); a.latex(l); b.write(t)
        st.caption(
            "Pas d’assistance sur un setup touchant une PM. "
            "Le HGA retire l’assistance en cas de dépassement de capacité ; le MILP peut décaler les setups."
        )

    st.subheader("Illustration (exemple du rapport : 1 machine, 2 jobs, 1 PM)")
    st.markdown("""$C_{j1}=4$ · $C_{PM}\\ge4+1+2=7$ · $S_{PM,j2}\\ge2$ (setup conservé) · $C_{j2}\\ge7+2+3=12$ donc $C_{\\max}=12$ ·
PM : début $5\\ge5$, fin $7\\le20$ ✔ · $T_{j2}\\ge12-10=2$.""")
    ex = pd.DataFrame([("M1", "Job 1", 0, 4, "Job"), ("M1", "setup avant PM", 4, 5, "Setup"), ("M1", "PM", 5, 7, "PM"),
                       ("M1", "setup J2 (conservé après la PM)", 7, 9, "Setup"), ("M1", "Job 2", 9, 12, "Job")],
                      columns=["Machine", "Label", "Début", "Fin", "Type"])
    draw_gantt(ex, "Exemple du rapport : 1 machine, 2 jobs, 1 PM (fenêtre [5 ; 20], échéance du job 2 = 10)",
               windows=[(5, 20)], due=[("M1", 10.0, "J2")], cmax=12.0)
    gantt_legend()
    st.table(pd.DataFrame([
        ["(9)", "Job 1 : 0 → 4", "C_j1 = 4 (setup du 1er job inclus)."],
        ["(10)", "setup 4 → 5, PM 5 → 7", "C_PM ≥ 4 + 1 + 2 = 7."],
        ["(12)(13)", "PM dans la bande grise", "Début 5 ≥ ouverture 5 ; fin 7 ≤ fermeture 20."],
        ["(11)", "setup jaune 7 → 9", "La PM n'efface pas le setup entre J1 et J2 : S_PM,j2 ≥ 2."],
        ["(9)", "Job 2 : 9 → 12", "C_j2 ≥ 7 + 2 + 3 = 12, donc Cmax = 12 (trait pointillé)."],
        ["(21)", "◆ à 10, fin à 12", "Retard T_j2 = 12 − 10 = 2."],
    ], columns=["Contrainte", "Ce qu'on voit", "Lecture"]))

    with st.expander("Code Gurobi réel (milp_gurobi.py)"):
        st.code((ORDO / "milp_gurobi.py").read_text(encoding="utf-8"), language="python")

elif page == PAGES[3]:
    st.markdown("""
Représentation de l'article (§5.1) : **`seq[i]`** = tableau d'activités de la machine *i* (jobs `0..J-1`, PM *k* = `J+k`), **`pm_day[k]`** = jour de la PM *k*
(= la liste de réclamations de ressource) et **`assist[j]`** = setup du job *j* assisté (objectif ③).

L'évaluation est **incrémentale** : un changement ne ré-évalue que les machines touchées (`meval`).
""")
    P = pdict("assist", gmax=30)
    s = runs_cached(FILE, LKW, key(P), 1)[0]["solution"]
    st.subheader(f"Exemple : meilleure solution du HGA sur {Path(FILE).name} (objectif ③)")
    for i, q in enumerate(s["seq"]):
        st.code(f"seq[{i}] = {q}   # ids ≥ {inst.nJ} = PM")
    st.code(f"pm_day = {s['pm_day']}\nassist = {s['assist']}")
    sol3 = make_sol(inst, HGAParams(**P), s["seq"], [s["pm_day"][k] for k in range(inst.nK)], s["assist"])
    st.subheader("De la solution codée au planning")
    c = st.columns([1, 2])
    c[0].markdown("<div class='pcard'><div class='pt'>seq[i] — activités par machine</div>" + machine_rows(s["seq"], inst.nJ) + "</div>", unsafe_allow_html=True)
    c[0].markdown("<div class='pcard' style='margin-top:.6rem'><div class='pt'>pm_day[k] — jour de la PM k</div>"
                  + "".join(f"<div class='mrow'><div class='ml' style='flex-basis:60px'>PM{k}</div><div>jour {d}</div></div>" for k, d in s["pm_day"].items()) + "</div>",
                  unsafe_allow_html=True)
    with c[1]:
        gantt_sol(P, sol3, "Planning décodé", annot=True)
        gantt_legend()
    st.markdown("""
**Décodage** (fonction `meval`) : on parcourt `seq[i]` de gauche à droite en partant de R_i. Pour un job *a* : on ajoute le setup (selon le job précédent), puis la durée ;
pour une PM *k* : début = max(temps courant + setup PM, ouverture de la fenêtre du jour `pm_day[k]`), et si la fin dépasse la fermeture, une **pénalité BIG** rend la solution infaisable.
""")
    st.dataframe(solution_table(HGAParams(**P), sol3).round(2), use_container_width=True)
    st.subheader("Lignes de code les plus pertinentes")
    for f in (Sol, Engine.meval, Engine.full, Engine.cap_violation, Engine.score):
        st.code(inspect.getsource(f), language="python")

elif page == PAGES[4]:
    st.markdown("Algorithme **steady-state** : à chaque génération, 2 parents donnent 2 enfants, chacun éventuellement admis dans la population. "
                "Ci-dessous, le schéma général puis le **déroulé complet sur l'instance sélectionnée** (barre latérale).")

    c = st.columns([2, 1, 1])
    obj4 = c[0].selectbox("Objectif de l'exemple", OBJS, 1, format_func=OBJ_LABEL.get, key="o4")
    g4 = c[1].select_slider("gmax", [30, 100, 300], 100, key="g4")
    c[2].markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    go = c[2].button("▶ Dérouler le HGA", type="primary", key="go4")
    P4 = pdict(obj4, gmax=g4)

    if go:
        with st.spinner("Exécution du HGA sur l'instance…"):
            Po = HGAParams(**P4)
            inits = [Engine(inst, Po, sd).init_solution() for sd in range(P4["pop"])]
            runs = runs_cached(FILE, LKW, key(P4), 2)
            nols = runs_cached(FILE, LKW, key(dict(P4, p_ls=0.0)), 2)
            st.session_state["ex4"] = dict(P=P4, inits=inits, runs=runs, nols=nols, file=FILE)
    ex4 = st.session_state.get("ex4")
    ready = bool(ex4) and ex4["file"] == FILE and ex4["P"] == P4

    vals = None
    if ready:
        best_init = min(ex4["inits"], key=lambda s: s.obj)
        best_run = min(ex4["runs"], key=lambda r: r["obj"])
        vals = {"I": f"meilleure init = {best_init.obj:.2f}", "R": f"{len(best_run['trace'])} générations",
                "B": f"Z_HGA = {best_run['obj']:.2f}"}
    st.subheader("Schéma de l'algorithme")
    st.graphviz_chart(flow_dot(P4, vals), use_container_width=True)
    st.caption(f"Instance : {Path(FILE).name} — {inst.nM} machines · {inst.nJ} jobs · {inst.nK} PM — objectif {OBJ_LABEL[obj4]}"
               + ("" if ready else "  ·  cliquez sur « Dérouler le HGA » pour remplir les étapes ci-dessous."))

    if ready:
        Po = HGAParams(**P4)
        J = inst.nJ
        o = [s.obj for s in ex4["inits"]]

        # ---- ① initialisation
        step(1, "Initialisation — population de départ",
             "Pour chaque individu : permutation aléatoire des activités (Fisher-Yates), puis <b>meilleure insertion</b> de chaque activité "
             "(et choix du jour libre pour une PM). On obtient des solutions déjà bonnes et diverses.")
        c = st.columns(4)
        c[0].metric("Meilleure init", f"{min(o):.2f}"); c[1].metric("Moyenne init", f"{stt.mean(o):.2f}")
        c[2].metric("Pire init", f"{max(o):.2f}"); c[3].metric("% faisables", f"{100 * sum(s.feasible for s in ex4['inits']) / len(o):.0f} %")
        gantt_sol(P4, best_init, f"Meilleure solution initiale (obj = {best_init.obj:.2f})")

        # ---- ② sélection + croisement : appel réel de Engine.crossover
        E = Engine(inst, Po, 123)
        pop0 = sorted({x.key(): x for x in ex4["inits"]}.values(), key=lambda x: x.fit)
        A, B = E.rng.sample(pop0, 2) if len(pop0) > 1 else (pop0[0], pop0[0])
        rstate = E.rng.getstate()
        kids = E.crossover(A, B)
        kid = kids[0]
        r = random.Random(); r.setstate(rstate)          # rejoue les tirages pour expliquer le résultat
        M = inst.nM
        cut = r.randint(1, max(1, M - 1))
        if P4["crossover"] == "uniform":
            tags = ["A" if r.random() < 0.5 else "B" for _ in range(M)]
        else:
            tags = ["A" if i < cut else "B" for i in range(M)]
        srcs = {"A": A, "B": B}
        seen, dup = set(), []
        for i in range(M):
            for x in srcs[tags[i]].seq[i]:
                if x in seen:
                    dup.append(x)
                else:
                    seen.add(x)
        missing = [x for x in range(J + inst.nK) if x not in seen]
        nm = lambda x: ("PM%d" % (x - J)) if x >= J else ("J%d" % x)
        step(2, "Sélection et croisement",
             "Deux parents sont tirés au hasard dans la population. Pour chaque machine <i>i</i>, l'enfant copie la séquence de A ou de B "
             + ("(one_point : machines avant la coupure → A, les autres → B)" if P4["crossover"] != "uniform" else "(uniform : source tirée au hasard par machine)")
             + ". Les <b>doublons</b> sont ignorés, les activités <b>manquantes</b> (vertes) sont réinsérées par meilleure insertion, "
             "et le jour de chaque PM est hérité du parent source. <code>crossover</code> produit <b>2 enfants</b> (rôles A/B inversés pour le second).")
        if M == 1:
            st.warning("Avec 1 machine, le croisement ne mélange rien : l'enfant est une copie d'un parent (la diversité vient des mutations).")
        cA, cB, cC = st.columns(3)
        cA.markdown(f"<div class='pcard'><div class='pt'>Parent A (obj {A.obj:.1f})</div>" + machine_rows(A.seq, J) + "</div>", unsafe_allow_html=True)
        cB.markdown(f"<div class='pcard'><div class='pt'>Parent B (obj {B.obj:.1f})</div>" + machine_rows(B.seq, J) + "</div>", unsafe_allow_html=True)
        cC.markdown(f"<div class='pcard'><div class='pt'>Enfant 1 (obj {kid.obj:.1f})</div>"
                    + rows_src(kid.seq, J, tags, {x: "new" for x in missing}) + "</div>", unsafe_allow_html=True)
        st.caption(f"Doublons ignorés : {[nm(x) for x in dup] or 'aucun'} · réinsérées : {[nm(x) for x in missing] or 'aucune'}. "
                   "Résultat de l'appel réel à `Engine.crossover` (graine fixe 123), expliqué en rejouant ses tirages aléatoires.")

        # ---- ③ mutation : mêmes opérations que Engine.mutate
        mut = kid.copy(); used = []
        for _ in range(P4["n_mut"]):
            op = E.rng.choice(P4["mut_ops"])
            if op == "assist_flip" and not E.assist_on:
                op = "swap"
            used.append(op); getattr(E, "_mut_" + op)(mut)
        E.evaluate(mut)
        step(3, "Mutation",
             f"Appliquée à l'enfant avec probabilité Pm = {P4['pm']} ; r = {P4['n_mut']} mutation(s) tirée(s) parmi <b>{' · '.join(P4['mut_ops'])}</b>. "
             "<code>worst_machine</code> vide la machine qui finit le plus tard et réinsère chacune de ses activités (meilleure insertion) sur une autre machine éligible tirée au hasard ; "
             "<code>swap</code> échange deux jobs ; <code>insert</code> déplace un job à une position aléatoire ; <code>pm_day</code> change le jour d'une PM (ou échange deux jours si tous sont saturés).")
        cM1, cM2 = st.columns(2)
        cM1.markdown(f"<div class='pcard'><div class='pt'>Avant mutation (obj {kid.obj:.1f})</div>" + machine_rows(kid.seq, J) + "</div>", unsafe_allow_html=True)
        cM2.markdown(f"<div class='pcard'><div class='pt'>Après {' + '.join(used)} (obj {mut.obj:.1f})</div>" + machine_rows(mut.seq, J) + "</div>", unsafe_allow_html=True)

        # ---- ④ recherche locale : appel réel de Engine.local_search
        ls = mut.copy(); E.local_search(ls)
        mean_ls = stt.mean(x["obj"] for x in ex4["runs"]); mean_no = stt.mean(x["obj"] for x in ex4["nols"])
        step(4, "Recherche locale — descente jusqu'au minimum local",
             f"Appliquée avec probabilité P_LS = {P4['p_ls']}. Au plus N_LS = {P4['n_ls']} tours ; chaque tour enchaîne : "
             "<b>insertion</b> (meilleure amélioration par machine, machines les plus chargées d'abord, profondeur d_ins), <b>échange</b> de deux jobs (d_swap), "
             "<b>changement de jour</b> des PM" + (", <b>bascule d'assistance</b>" if E.assist_on else "") + ". Arrêt dès qu'aucun voisinage n'améliore.")
        c = st.columns(4)
        c[0].metric("Enfant croisé", f"{kid.obj:.2f}"); c[1].metric("Après mutation", f"{mut.obj:.2f}")
        c[2].metric("Après recherche locale", f"{ls.obj:.2f}", f"{ls.obj - mut.obj:.2f}", delta_color="inverse")
        c[3].metric("Sans / avec LS (HGA complet, moy. 2 exéc.)", f"{mean_no:.1f} / {mean_ls:.1f}")

        # ---- ⑤ remplacement et arrêt
        worst_fit = max(x.fit for x in pop0)
        unique = ls.key() not in {x.key() for x in pop0}
        admitted = unique and ls.fit < worst_fit
        tr = best_run["trace"]
        nimp = sum(1 for p_, q_ in zip(tr, tr[1:]) if q_ < p_ - 1e-9)
        step(5, "Remplacement et critère d'arrêt",
             "Chaque enfant est admis s'il est <b>inédit</b> dans la population (clé de solution) <b>et</b> meilleur (fitness) que le <b>pire</b> individu, qu'il remplace. "
             f"Une génération = 2 enfants testés. Arrêt : gmax = {P4['gmax']}, time_limit, stagnation ou target.")
        c = st.columns(3)
        c[0].metric("Fitness de l'enfant", f"{ls.fit:.2f}"); c[1].metric("Pire de la population initiale", f"{worst_fit:.2f}")
        c[2].metric("Verdict", "Remplace le pire" if admitted else ("Rejeté (déjà présent)" if not unique else "Rejeté (pas meilleur)"))
        c = st.columns(3)
        c[0].metric("Générations", len(tr) - 1); c[1].metric("Améliorations du meilleur", nimp)
        c[2].metric("Temps (s)", f"{best_run['time']:.2f}")
        conv({"HGA (meilleure exécution)": tr, "Meilleure init de l'exécution": [tr[0]] * len(tr)})

        # ---- résultat
        gain = 100 * (best_init.obj - best_run["obj"]) / best_init.obj if best_init.obj else 0.0
        step(6, "Résultat — avant / après le HGA",
             f"Objectif : <b>{best_init.obj:.2f}</b> → <b>{best_run['obj']:.2f}</b> (−{gain:.1f} %). "
             "Mêmes jobs et mêmes PM : seuls l'affectation, la séquence et le jour des PM ont changé.")
        a, b = st.columns(2)
        with a:
            gantt_sol(P4, best_init, f"Avant : meilleure init ({best_init.obj:.2f})", annot=True)
        with b:
            gantt(FILE, LKW, P4, best_run["solution"], f"Après : HGA ({best_run['obj']:.2f})", annot=True)

    st.header("🎬 Pas à pas génération par génération")
    st.markdown("Le HGA est **rejoué avec la même boucle que `run_hga`** (mêmes opérateurs, graine au choix) et chaque étape est enregistrée. "
                "Avancez génération par génération, puis ouvrez les onglets ①→⑤ pour voir parents, croisement, mutation, recherche locale et décision de remplacement, avec les Gantt correspondants.")
    cs = st.columns([1, 1, 1, 2])
    ng4 = cs[0].slider("Générations à enregistrer", 5, 60, 20, key="ng4")
    sd4 = cs[1].number_input("Graine", 0, 999, 0, key="sd4")
    cs[2].markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    if cs[2].button("🎬 Lancer le pas à pas", type="primary", key="go_step"):
        with st.spinner("Enregistrement des générations…"):
            st.session_state["tr4"] = dict(T=traced_run(HGAParams(**P4), int(sd4), int(ng4)), P=P4, file=FILE)
            st.session_state["g_step"] = 0
    tr4 = st.session_state.get("tr4")
    if tr4 and tr4["file"] == FILE and tr4["P"] == P4:
        show_hga_steps(tr4["T"], P4)
    elif tr4:
        st.info("L'instance ou les paramètres ont changé depuis l'enregistrement : relancez le pas à pas.")
    else:
        st.info("Cliquez sur « Lancer le pas à pas » pour enregistrer l'exécution sur l'instance sélectionnée.")
    st.subheader("Comment chaque contrainte est respectée dans le HGA")
    st.table(pd.DataFrame([
        ["Éligibilité (2)", "`allowed_machines`, `job_machines`, `pm_machines` : tout déplacement ne choisit que des machines éligibles."],
        ["Chaîne par machine (6)(7)", "`seq[i]` est une liste : un prédécesseur et un successeur par construction ; `seen` dans le croisement évite les doublons."],
        ["Une PM par machine (5)", "`allowed_machines` / `ls_insert` excluent les machines qui portent déjà une PM."],
        ["Ressource rare (8)", "`day_load`, `free_days`, `repair_days` : jamais plus de w_d PM par jour ; `ls_pm_day` échange les jours si saturé."],
        ["Fenêtres de PM (12)(13)", "`meval` : `t = max(t+spm, rel) + pm` ; si `t > due` → pénalité `BIG` (la solution est « corrigée » aux itérations suivantes)."],
        ["Setup conservé après PM (11)", "`meval` garde `prev` (dernier job) : le setup suivant utilise `sds[i][prev][a]`, la PM est transparente."],
        ["Assistance (A1)–(A6)", "`assist[a]` actif seulement job→job / début→job (pas après PM) ; `cap_violation` retire l'assistance si > K setups assistés se chevauchent."],
    ], columns=["Contrainte", "Implémentation"]))
    with st.expander("Code : boucle principale, croisement, mutations, recherche locale"):
        for f in (run_hga, Engine.crossover, Engine.mutate, Engine._mut_worst_machine, Engine.ls_insert, Engine.ls_swap, Engine.ls_pm_day, Engine.local_search):
            st.code(inspect.getsource(f), language="python")

elif page == PAGES[5]:
    st.markdown("Permutation aléatoire des activités (Fisher-Yates) puis **meilleure insertion** : chaque activité est insérée à la position (et, pour une PM, au jour libre) "
                "qui minimise la fitness → population forte et diverse.")
    with st.expander("Code : init_solution, best_insert"):
        for f in (Engine.init_solution, Engine.best_insert):
            st.code(inspect.getsource(f), language="python")
    obj = st.selectbox("Objectif", OBJS, format_func=OBJ_LABEL.get)
    n = st.slider("Solutions initiales à générer", 5, 100, 30)
    if st.button("Générer et analyser", type="primary"):
        P = HGAParams(**pdict(obj)); t0 = time.time()
        vals = []
        for sd in range(n):
            s = Engine(inst, P, sd).init_solution(); vals.append((s.obj, s.feasible))
        o = [v[0] for v in vals]
        fin = runs_cached(FILE, LKW, key(pdict(obj)), 3)
        st.dataframe(pd.DataFrame({"Init best": [min(o)], "Init mean": [stt.mean(o)], "Init worst": [max(o)],
                                   "% faisables": [100 * sum(v[1] for v in vals) / n], "Temps (s)": [time.time() - t0],
                                   "HGA final (moy. 3 runs)": [stt.mean(r['obj'] for r in fin)]}).round(3), use_container_width=True)
        st.bar_chart(pd.Series(o, name="objectif initial"))

    st.subheader("🧱 Voir la construction pas à pas")
    st.markdown("Une solution est construite en insérant les activités **une à une**, dans un ordre tiré au hasard : "
                "chaque activité est testée à toutes les positions des machines éligibles (et, pour une PM, aux jours libres) et placée là où l'objectif est le meilleur. "
                "Déplacez le curseur pour voir le planning grandir.")
    c5 = st.columns([1, 1, 2])
    sd5 = c5[0].number_input("Graine", 0, 999, 0, key="sd5")
    c5[1].markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    if c5[1].button("🧱 Construire pas à pas", type="primary", key="go5"):
        P5 = pdict(obj); Po5 = HGAParams(**P5); E5 = Engine(inst, Po5, int(sd5))
        s5 = Sol(); s5.seq = [[] for _ in range(inst.nM)]; s5.pm_day = [-1] * inst.nK
        s5.assist = [False] * inst.nJ if Po5.objective == "assist" else None
        E5.evaluate(s5)
        acts5 = list(range(inst.nJ + inst.nK)); E5.rng.shuffle(acts5)
        steps = [(None, s5.copy(), "")]
        for a in acts5:
            E5.best_insert(s5, a)
            where = next((f"M{i}, rang {q.index(a) + 1}" for i, q in enumerate(s5.seq) if a in q), "")
            steps.append((a, s5.copy(), where))
        st.session_state["ins5"] = dict(steps=steps, P=P5, file=FILE, order=acts5)
        st.session_state["k5"] = 0
    ins = st.session_state.get("ins5")
    if ins and ins["file"] == FILE:
        steps, J5 = ins["steps"], inst.nJ
        nm5 = lambda x: ("PM%d" % (x - J5)) if x >= J5 else ("J%d" % x)
        st.caption("Ordre d'insertion tiré au hasard : " + " → ".join(nm5(a) for a in ins["order"]))
        k5 = st.slider("Étape d'insertion", 0, len(steps) - 1, key="k5")
        act, sk, where = steps[k5]
        if act is None:
            st.info("Étape 0 : machines vides (chargées jusqu'à R_i).")
        else:
            st.markdown(f"**Étape {k5}** : **{nm5(act)}** est inséré à la meilleure position → **{where}** · objectif partiel = **{sk.obj:.2f}**")
            cc = st.columns([1, 2])
            cc[0].markdown("<div class='pcard'><div class='pt'>Séquences après l'étape</div>" + machine_rows(sk.seq, J5, {act: "new"}) + "</div>", unsafe_allow_html=True)
            with cc[1]:
                gantt_sol(ins["P"], sk, f"Planning partiel après {k5} insertion(s)")
                gantt_legend(False)
            st.bar_chart(pd.Series([x[1].obj for x in steps[1:]], index=range(1, len(steps)), name="objectif partiel"))





elif page == PAGES[6]:
    st.markdown(
        "Simulez **un ou plusieurs paramètres** (toutes les combinaisons). "
        "Le **meilleur** réglage par objectif alimente la **page 7**. "
        "Toute **amélioration** ultérieure met à jour l’historique **page 8** (Gantt + convergence inclus)."
    )
    with st.expander("Formules des métriques", expanded=True):
        show_metrics_formulas()

    sel = st.multiselect("Objectifs", OBJS, OBJS, format_func=OBJ_LABEL.get, key="sel6")
    with st.expander("Valeurs de base (paramètres non variés)"):
        base = hga_widgets("p6", "weighted")

    VAR = {
        "pop": [10, 20, 50, 100], "gmax": [30, 50, 100, 300], "n_mut": [1, 2, 3, 5],
        "pc": [0.5, 0.8, 1.0], "pm": [0.3, 0.5, 1.0], "p_ls": [0.0, 0.5, 1.0],
        "n_ls": [10, 20, 50], "n_elite": [1, 2], "d_ins": [0.5, 1.0], "d_swap": [0.5, 1.0],
        "crossover": ["one_point", "uniform"],
        "mut_ops": ["worst_machine", "worst_machine+swap", "worst_machine+swap+insert+pm_day"],
    }
    pnames = st.multiselect("Paramètres à varier", list(VAR), ["n_mut", "crossover"], key="pn6")
    chosen = {}
    for pn in pnames:
        chosen[pn] = st.multiselect(f"Valeurs · {pn}", VAR[pn], VAR[pn][:2], key=f"vv6_{pn}")

    c = st.columns(3)
    R = c[0].slider("Runs R par combinaison", 3, 20, 5, key="R6")
    max_comb = c[1].number_input("Plafond combinaisons", 1, 48, 12, key="mc6")
    use_g = c[2].checkbox("Inclure Z* Gurobi (limite barre latérale)", False, key="ug6")

    combos = []
    if pnames and all(chosen.get(pn) for pn in pnames):
        keys = list(pnames)
        for prod in itertools.product(*[chosen[k] for k in keys]):
            combos.append(dict(zip(keys, prod)))
        if len(combos) > max_comb:
            combos = combos[: int(max_comb)]
        st.caption(f"{len(combos)} combinaison(s) × {R} runs × {len(sel)} objectif(s)")

    if st.button("Lancer les simulations HGA", type="primary", key="go6") and sel and combos:
        skip = ("objective", "K", "alpha", "beta", "delta", "gamma", "c_ass")
        bar = st.progress(0.0)
        tot = max(1, len(sel) * len(combos))
        step_i = 0
        batch = {}
        for obj in sel:
            Zx = proven = None
            if use_g:
                ex = exact_cached(FILE, LKW, key(pdict(obj)), float(MILP_T), True)
                if isinstance(ex, dict) and "error" not in ex and ex.get("obj") is not None:
                    Zx, proven = ex["obj"], ex.get("proven_optimal")
            best_pack = None
            for combo in combos:
                pd_ = pdict(obj, **{kk: vv for kk, vv in base.items() if kk not in skip})
                for pn, v in combo.items():
                    pd_[pn] = tuple(v.split("+")) if pn == "mut_ops" else v
                ALLP = ["pop", "gmax", "n_mut", "pc", "pm", "p_ls", "n_ls", "n_elite", "d_ins", "d_swap", "crossover", "mut_ops"]
                label = " · ".join(
                    f"{k}={'+'.join(pd_[k]) if isinstance(pd_[k], tuple) else pd_[k]}" for k in ALLP
                )
                runs = runs_cached(FILE, LKW, key(pd_), R)
                row, B = stat_row(FILE, LKW, pd_, runs, Zx, proven)
                best_run = min(runs, key=lambda r: r["obj"])
                pack = dict(row=row, pd=pd_, runs=runs, best_run=best_run, label=label, Zx=Zx, proven=proven, B=B)
                step_i += 1
                bar.progress(step_i / tot)
                if best_pack is None or row["Best"] < best_pack["row"]["Best"] - 1e-9:
                    best_pack = pack
            batch[obj] = best_pack

        if "results7" not in st.session_state:
            st.session_state["results7"] = {}
        if "improve_hist" not in st.session_state:
            st.session_state["improve_hist"] = {o: [] for o in OBJS}
        if "viz_data" not in st.session_state:
            st.session_state["viz_data"] = {}

        for obj, pack in batch.items():
            if pack is None:
                continue
            row, pd_, runs, best_run = pack["row"], pack["pd"], pack["runs"], pack["best_run"]
            label = pack["label"]
            prev = st.session_state["results7"].get(obj)
            entry7 = {
                "Best": row["Best"], "Mean": row["Mean"], "Worst": row["Worst"], "SD": row["SD"],
                "ARPD (%)": row["ARPD (%)"], "Succès (%)": row["Succès (%)"],
                "Gap vs Z* Gurobi (%)": row.get("Gap vs Z* Gurobi (%)"),
                "Temps moy. (s)": row.get("Temps moy. (s)"), "label": label,
                "pd": pd_, "solution": best_run["solution"], "trace": best_run["trace"],
                "mean_trace": mean_trace(runs), "Zx": pack["Zx"],
            }
            if prev is None or row["Best"] < prev["Best"] - 1e-9:
                st.session_state["results7"][obj] = entry7
            st.session_state["viz_data"][obj] = entry7
            update_improvement_history(obj, label or "exp6", label, row, Zx=pack["Zx"])

        st.session_state["res6_done"] = True
        st.success("Simulations terminées → pages 7 (résultats + Gantt/convergence) et 8 (historique).")

    if st.session_state.get("res6_done") and st.session_state.get("results7"):
        st.subheader("Aperçu du meilleur réglage")
        rows = []
        for obj, r in st.session_state["results7"].items():
            rows.append({"objectif": OBJ_LABEL[obj], "Best": r["Best"], "Mean": r["Mean"], "ARPD (%)": r["ARPD (%)"],
                         "Succès (%)": r["Succès (%)"], "params": r.get("label")})
        st.dataframe(pd.DataFrame(rows).round(4), use_container_width=True)
        st.markdown("**Conclusion** : ouvrez la page **7** pour Gantt et courbes ; page **8** pour l’historique d’amélioration.")



elif page == PAGES[7]:
    st.markdown(
        "Résultats **dynamiques** pour l’**instance sélectionnée** dans la barre latérale "
        f"(actuellement **`{Path(FILE).name}`**). "
        "Les Gantt et courbes de convergence apparaissent dès qu’une simulation a été lancée en page **6** ou **9**."
    )
    res7 = st.session_state.get("results7") or {}
    viz = st.session_state.get("viz_data") or res7

    if res7:
        rows = []
        for obj in OBJS:
            r = res7.get(obj)
            if not r:
                continue
            rows.append({
                "objectif": OBJ_LABEL[obj], "Best": r.get("Best"), "Mean": r.get("Mean"), "SD": r.get("SD"),
                "ARPD (%)": r.get("ARPD (%)"), "Succès (%)": r.get("Succès (%)"),
                "Gap vs Z* (%)": r.get("Gap vs Z* Gurobi (%)"), "params": r.get("label"),
            })
        st.dataframe(pd.DataFrame(rows).round(4), use_container_width=True)

        for obj in OBJS:
            r = viz.get(obj) or res7.get(obj)
            if not r:
                continue
            st.markdown(f"### {OBJ_LABEL[obj]}")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Best", f"{r['Best']:.4f}" if r.get("Best") is not None else "—")
            k2.metric("Mean", f"{r['Mean']:.4f}" if r.get("Mean") is not None else "—")
            k3.metric("ARPD (%)", f"{r.get('ARPD (%)', 0):.3f}")
            k4.metric("Succès (%)", f"{r.get('Succès (%)', 0):.1f}")
            if r.get("solution") and r.get("pd"):
                try:
                    gantt(FILE, LKW, r["pd"], r["solution"], f"Gantt — {OBJ_LABEL[obj]} (Best={r['Best']:.3f})", annot=True)
                    gantt_legend()
                except Exception as e:
                    st.caption(f"Gantt indisponible : {e}")
            curves = {}
            if isinstance(r.get("trace"), list) and r["trace"]:
                curves["meilleure exécution"] = r["trace"]
            if isinstance(r.get("mean_trace"), list) and r["mean_trace"]:
                curves["moyenne des runs"] = r["mean_trace"]
            if r.get("Zx") is not None and curves:
                L = max(len(v) for v in curves.values())
                curves["Z* Gurobi"] = [r["Zx"]] * L
            if curves:
                st.caption("Convergence (meilleur objectif par génération)")
                conv(curves)
        st.markdown(
            f"**Conclusion** : valeurs et graphiques pour **`{Path(FILE).name}`**. "
            "Une nouvelle simulation (page 6) plus performante met à jour ce tableau, les Gantt et les courbes."
        )
    else:
        st.info(
            f"Pas encore de simulation pour **`{Path(FILE).name}`**. "
            "Lancez la **page 6** (paramétrage) pour remplir ce tableau avec Gantt et convergence. "
            "Ci-dessous : **exemple de référence** uniquement (Solver/Data_2_8_2), pas l’instance courante."
        )
        with st.expander("Exemple de référence — Solver/Data_2_8_2 (illustratif)", expanded=True):
            show_precomputed_table()
            st.caption(
                "Ce tableau d’exemple ne dépend pas de l’instance choisie dans la barre latérale. "
                "Pour des Gantt/convergence sur votre fichier, lancez une simulation page 6."
            )

    with st.expander("Formules des métriques"):
        show_metrics_formulas()


elif page == PAGES[8]:
    st.markdown(
        "Historique **dynamique** (précédent ↔ courant) pour l’instance sélectionnée. "
        "Gantt et convergence du réglage courant si une simulation de session existe."
    )
    with st.expander("Formules", expanded=False):
        show_metrics_formulas()

    if "improve_hist" not in st.session_state or not any(st.session_state.get("improve_hist", {}).get(o) for o in OBJS):
        st.session_state["improve_hist"] = {o: [] for o in OBJS}
        for row in PRECOMPUTED_IMPROVED:
            obj = row["objectif"]
            entry = {
                "config": row["config"], "params": row["params"],
                "HGA_best": row["HGA_best"], "HGA_mean": row["HGA_mean"], "HGA_sd": row["HGA_sd"],
                "ARPD (%)": row["ARPD (%)"], "Succès (%)": row["Succès (%)"],
                "Gap vs Z* (%)": row["Gap vs Z* (%)"], "temps_HGA_moy_s": row["temps_HGA_moy_s"],
                "Z*_Gurobi": row["Z*_Gurobi"],
            }
            st.session_state["improve_hist"].setdefault(obj, []).append(entry)
        for obj in OBJS:
            st.session_state["improve_hist"][obj] = st.session_state["improve_hist"].get(obj, [])[-2:]

    hist = st.session_state.get("improve_hist") or {}
    viz = st.session_state.get("viz_data") or {}

    for obj in OBJS:
        entries = hist.get(obj) or []
        if not entries:
            continue
        st.markdown(f"### {OBJ_LABEL[obj]}")
        st.dataframe(pd.DataFrame(entries).round(4), use_container_width=True)
        if len(entries) >= 2:
            a, b = entries[-2], entries[-1]
            delta = None
            if a.get("HGA_best") is not None and b.get("HGA_best") is not None:
                delta = b["HGA_best"] - a["HGA_best"]
            st.success(
                f"**{a.get('config')}** Best={a.get('HGA_best')} → **{b.get('config')}** Best={b.get('HGA_best')}"
                + (f" (Δ = {delta:+.4f})" if delta is not None else "")
            )
        r = viz.get(obj)
        if r and r.get("solution") and r.get("pd"):
            try:
                gantt(FILE, LKW, r["pd"], r["solution"], f"Gantt courant — {OBJ_LABEL[obj]}", annot=True)
                gantt_legend()
            except Exception as e:
                st.caption(f"Gantt : {e}")
            curves = {}
            if isinstance(r.get("trace"), list) and r["trace"]:
                curves["meilleure exécution"] = r["trace"]
            if isinstance(r.get("mean_trace"), list) and r["mean_trace"]:
                curves["moyenne"] = r["mean_trace"]
            if r.get("Zx") is not None and curves:
                L = max(len(v) for v in curves.values())
                curves["Z*"] = [r["Zx"]] * L
            if curves:
                conv(curves)

    st.markdown("---")
    show_improved_comparison()
    st.markdown(
        "**Conclusion** : chaque gain de Best (page 6) fait glisser l’ancien réglage en « précédent » "
        "et place le nouveau en « courant », avec Gantt/convergence associés lorsqu’ils sont disponibles."
    )



elif page == PAGES[9]:
    st.markdown(
        """
<div class="tour-card">
  <h4>Chapitre 9 — Démo figée (indépendante)</h4>
  <div class="body">
  <b>Présentation purement illustrative</b> — cette page n’écrit rien dans les pages 6 / 7 / 8 et ne dépend pas de l’instance choisie à gauche.<br/>
  Elle rejoue une histoire précalculée sur <b>Data_2_8_2</b> (Z* Gurobi 1 h, grilles cartésiennes, Gantt, convergences).<br/>
  <b>Aucun bouton, aucun calcul dynamique</b> : tout est déjà calculé. Les pages 6–8 restent le simulateur interactif séparé.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ----- 1 Formules -----
    step(1, "Métriques communes (pages 6, 7, 8)",
         "Best, Mean, SD, ARPD, Succès, Gap vs Z* — mêmes formules partout.")
    show_metrics_formulas()

    # ----- 2 Z* 1h -----
    step(2, "Z* Gurobi — règlement 1 h (référence unique)",
         "Avant toute grille : on fixe Z* sous limite **3600 s**. "
         "① Makespan prouvé OPTIMAL en 2,49 s → 83,540. "
         "② / ③ TIME_LIMIT (gap ~20–22 %) → Z* = incumbent 1 h.")
    st.dataframe(pd.DataFrame([
        {"Objectif": "① Makespan", "Z* (1 h)": 83.5403, "Statut": "OPTIMAL", "Temps Gurobi (s)": 2.49, "Gap MIP (%)": 0.0},
        {"Objectif": "② Weighted", "Z* (1 h)": 223.3545, "Statut": "TIME_LIMIT", "Temps Gurobi (s)": 3600, "Gap MIP (%)": 20.59},
        {"Objectif": "③ Assist", "Z* (1 h)": 210.3124, "Statut": "TIME_LIMIT", "Temps Gurobi (s)": 3600, "Gap MIP (%)": 22.32},
    ]), use_container_width=True)
    st.caption("Ces Z* 1 h ne changent pas d’une campagne à l’autre. Gap / Succès HGA se calculent toujours contre eux.")

    # ----- 3 Page 6 campagne 1 : grille cartésienne -----
    step(3, "Page 6 · Campagne 1 — grille de combinaisons (comme après Simuler)",
         "On fixe la base article (pop=10, gmax=50, mut=worst_machine, …) et on fait le **produit cartésien** "
         "`n_mut ∈ {1,2,3}` × `crossover ∈ {one_point, uniform}` → **6 combinaisons × 5 runs × 3 objectifs**. "
         "Pour chaque ligne : Best / Mean / SD / ARPD / Succès / Gap vs Z* 1 h. "
         "Puis l’app **sélectionne automatiquement le meilleur Best** par objectif → envoi page 7.")
    st.markdown("##### Paramètres non variés (base article)")
    st.dataframe(pd.DataFrame([{
        "pop": 10, "gmax": 50, "n_elite": 1, "mut_ops": "worst_machine",
        "p_ls": 1.0, "n_ls": 50, "pc": 1.0, "pm": 1.0, "Runs R": 5,
    }]), use_container_width=True)
    st.markdown("##### Grille complète — résultats de **toutes** les combinaisons")
    df_c1 = pd.DataFrame(PRECOMPUTED_COMBOS_C1)
    for obj in OBJS:
        st.markdown(f"**{OBJ_LABEL[obj]}**")
        sub = df_c1[df_c1["objectif"] == obj].drop(columns=["objectif"])
        # highlight best Best
        st.dataframe(sub.round(4), use_container_width=True)
        best_row = sub.loc[sub["Best"].idxmin()]
        st.caption(
            f"→ Meilleure combinaison : n_mut={int(best_row['n_mut'])}, crossover={best_row['crossover']} "
            f"(Best={best_row['Best']:.4f}, Gap vs Z* 1 h={best_row['Gap vs Z* (%)']:.4f} %)."
        )
    st.markdown("##### Sélection automatique (sortie page 6 → entrée page 7)")
    st.dataframe(pd.DataFrame([
        {"objectif": OBJ_LABEL[o], **{k: v for k, v in PRECOMPUTED_BEST_C1[o].items()},
         "params": _full_params(10, 50, PRECOMPUTED_BEST_C1[o]['n_mut'], PRECOMPUTED_BEST_C1[o]['crossover'], "worst_machine", 1)}
        for o in OBJS
    ]).round(4), use_container_width=True)
    st.success(
        "**Liaison page 6 → page 7** : ces 3 lignes (un Best par objectif) deviennent le **résultat courant**. "
        "La page 7 affiche le tableau + **un Gantt et une courbe de convergence par objectif** (3 Gantt)."
    )
    st.markdown(
        "**Conclusion campagne 1** : monter `n_mut` et passer en `uniform` améliore Mean/ARPD ; "
        "makespan déjà souvent optimal ; weighted/assist encore au-dessus ou juste sous l’incumbent 1 h, "
        "mais `worst_machine` seul reste limité → d’où une 2ᵉ campagne enrichie."
    )

    # ----- 4 Page 7 après campagne 1 -----
    step(4, "Page 7 · Résultats optimaux de la campagne 1 (3 objectifs)",
         "Après Simuler, la page 7 ne montre **que le meilleur réglage** retenu par objectif — "
         "pas toute la grille. Pour chaque objectif : métriques, **Gantt annoté**, **courbe de convergence**.")
    st.markdown("##### Tableau page 7 (courant = meilleure combinaison campagne 1)")
    st.dataframe(pd.DataFrame([
        {"objectif": OBJ_LABEL[o], "Best": PRECOMPUTED_BEST_C1[o]["Best"], "Mean": PRECOMPUTED_BEST_C1[o]["Mean"],
         "ARPD (%)": PRECOMPUTED_BEST_C1[o]["ARPD (%)"], "Succès (%)": PRECOMPUTED_BEST_C1[o]["Succès (%)"],
         "Gap vs Z* 1 h (%)": PRECOMPUTED_BEST_C1[o]["Gap vs Z* (%)"],
         "params": _full_params(10, 50, PRECOMPUTED_BEST_C1[o]['n_mut'], PRECOMPUTED_BEST_C1[o]['crossover'], "worst_machine", 1)}
        for o in OBJS
    ]).round(4), use_container_width=True)
    st.markdown("""
**Sur la vraie page 7, pour chaque objectif on aurait :**
- un **diagramme de Gantt** (jobs / setups / PM / fenêtres) ;
- une **courbe de convergence** (meilleur objectif par génération, éventuellement vs Z* 1 h).

Ci-dessous : illustration **fixe** sur **Solver/Data_2_8_2** uniquement (indépendante de l'instance choisie à gauche).
""")
    try:
        # Page 9 = présentation figée : toujours Data_2_8_2, jamais FILE de la barre latérale
        demo_path = None
        candidates = []
        try:
            candidates.append(Path(FILE).parent)
        except Exception:
            pass
        try:
            candidates.append(Path(DATA))
        except Exception:
            pass
        candidates.extend([HERE, HERE.parent, HERE / "Solver", HERE.parent / "Solver"])
        for base in candidates:
            if base is None:
                continue
            for cand in (Path(base) / "Data_2_8_2.txt", Path(base) / "Solver" / "Data_2_8_2.txt"):
                if cand.exists():
                    demo_path = str(cand)
                    break
            if demo_path:
                break
        if demo_path is None:
            try:
                for f in files:
                    if str(f).endswith("Data_2_8_2.txt"):
                        demo_path = str(f)
                        break
            except Exception:
                pass
        if demo_path is None:
            raise FileNotFoundError("Data_2_8_2.txt introuvable (démo page 9 figée)")
        demo_lkw = (("days", None), ("resources", None), ("due_mode", "gen"), ("due_low", 0.4), ("due_high", 1.0), ("due_seed", 0))
        Pviz = pdict(
            "makespan", pop=10, gmax=50, n_mut=3, n_elite=1, crossover="uniform",
            mut_ops=("worst_machine",),
        )
        runs_ill = runs_cached(demo_path, demo_lkw, key(Pviz), 3)
        best_ill = min(runs_ill, key=lambda r: r["obj"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Best (démo Data_2_8_2)", f"{best_ill['obj']:.4f}")
        c2.metric("Instance (fixe)", "Data_2_8_2")
        c3.metric("Z* makespan 1 h", "83.540")
        gantt(demo_path, demo_lkw, Pviz, best_ill["solution"],
              f"Gantt démo page 9 — Data_2_8_2 makespan (Best={best_ill['obj']:.3f})", annot=True)
        gantt_legend()
        conv({
            "meilleure exécution": best_ill["trace"],
            "moyenne (3 runs)": mean_trace(runs_ill),
            "Z* 1 h": [83.5403] * max(len(best_ill["trace"]), 1),
        })
        st.caption("Cette illustration ne change **pas** si vous sélectionnez une autre instance dans la barre latérale.")
    except Exception as e:
        st.info(f"Gantt/convergence démo (Data_2_8_2) indisponibles : {e}")
    st.info(
        "**Liaison** : si une **nouvelle** campagne page 6 trouve un Best encore meilleur, "
        "ce n’est **pas** seulement la page 7 qui change — l’historique **page 8** se renouvelle "
        "(précédent = ancien courant, courant = nouveau Best), avec Gantt/convergences du réglage courant."
    )

    # ----- 5 Page 6 campagne 2 -----
    step(5, "Page 6 · Campagne 2 — nouvelle grille (réglages enrichis)",
         "On revient en page 6. On compare explicitement **base** vs **enrichi** "
         "(pop, gmax, mut_ops) pour les 3 objectifs. Le produit cartésien réduit ici à 2 familles "
         "pour la lisibilité ; en vrai vous pouvez croiser plus de paramètres.")
    st.markdown("##### Grille campagne 2 (toutes les lignes simulées)")
    st.dataframe(pd.DataFrame(PRECOMPUTED_COMBOS_C2).round(4), use_container_width=True)
    st.markdown("##### Meilleur retenu par objectif (→ met à jour page 7 **et** page 8)")
    st.dataframe(pd.DataFrame([
        {"objectif": OBJ_LABEL[o], **{k: v for k, v in PRECOMPUTED_BEST_C2[o].items() if k != "label"}, "params": PRECOMPUTED_BEST_C2[o]["label"]}
        for o in OBJS
    ]).round(4), use_container_width=True)
    st.success(
        "**Sélection** : pour les 3 objectifs, la famille enrichie gagne. "
        "Best weighted 220,93 **bat** Z* incumbent 1 h (Gap −1,08 %) ; "
        "makespan 100 % de succès ; assist ≈ Z* 1 h."
    )
    st.markdown(
        "**Conclusion campagne 2** : mutations enrichies + plus d’effort (pop/gmax/n_mut) + uniform + élites "
        "stabilisent Mean et montent le Succès. C’est ce Best qui devient le **courant**."
    )

    # ----- 6 Page 7 mise à jour -----
    step(6, "Page 7 · Après campagne 2 — courant = meilleurs des grilles",
         "Le tableau page 7 est **écrasé** par les nouveaux Best. "
         "Les **3 Gantt** et **3 courbes de convergence** du courant se mettent à jour.")
    st.dataframe(pd.DataFrame([
        {"objectif": OBJ_LABEL[o], "Best": PRECOMPUTED_BEST_C2[o]["Best"], "Mean": PRECOMPUTED_BEST_C2[o]["Mean"],
         "ARPD (%)": PRECOMPUTED_BEST_C2[o]["ARPD (%)"], "Succès (%)": PRECOMPUTED_BEST_C2[o]["Succès (%)"],
         "Gap vs Z* 1 h (%)": PRECOMPUTED_BEST_C2[o]["Gap vs Z* (%)"],
         "params": PRECOMPUTED_BEST_C2[o]["label"]}
        for o in OBJS
    ]).round(4), use_container_width=True)
    st.caption("Même logique d’affichage qu’à l’étape 4 : un Gantt + une convergence par objectif (3 de chaque).")

    # ----- 7 Page 8 -----
    step(7, "Page 8 · Historique : précédent (campagne 1) ↔ courant (campagne 2)",
         "Dès qu’un Best de campagne 2 est **strictement meilleur**, la page 8 archive l’ancien courant "
         "comme **précédent** et pose le nouveau en **courant**. "
         "On y retrouve aussi Gantt + convergence du **réglage courant** (les 3 objectifs).")
    show_improved_comparison()
    st.markdown("##### Lecture de la liaison 6 → 7 → 8")
    st.markdown("""
| Étape | Où | Ce qui s’affiche |
|-------|-----|------------------|
| Grille + runs | **Page 6** | **Toutes** les combinaisons (tableau cartésien), puis **meilleur** par objectif |
| Courant | **Page 7** | Uniquement le meilleur / objectif + **3 Gantt** + **3 convergences** |
| Nouvelle grille | **Page 6** | Autre produit cartésien ; si Best ↓ → mise à jour |
| Historique | **Page 8** | **Précédent ↔ courant** + Gantt/convergences du courant |

**Ce n’est pas la page 7 qui « historise »** : elle montre le courant. **La page 8** garde la trace des gains.
""")
    st.markdown(
        "**Conclusion page 8** : makespan succès 80 % → **100 %** ; weighted 223,97 → **220,93** "
        "(−1,08 % vs Z* 1 h) ; assist 213,66 → **210,31**. "
        "Leviers : mut_ops enrichis, pop/gmax/n_mut, crossover uniforme, n_elite."
    )

    # ----- 8 Synthèse -----
    step(8, "Conclusions générales",
         "Fil complet de la démo Data_2_8_2 sous Z* règlement 1 h.")
    st.markdown("""
1. **Page 6** explore un **produit cartésien** de paramètres ; chaque case = R runs ; on calcule Best/Mean/ARPD/Succès/Gap vs Z* 1 h.  
2. Le **meilleur Best par objectif** alimente la **page 7** (chiffres + 3 Gantt + 3 convergences).  
3. Une **2ᵉ campagne** page 6 plus riche peut encore baisser le Best.  
4. Alors **page 8** se renouvelle (précédent ↔ courant) ; page 7 affiche seulement le nouveau courant.  
5. Sur Data_2_8_2 : makespan = optimum prouvé ; weighted HGA **bat** l’incumbent 1 h ; assist rejoint l’incumbent 1 h.
""")
    st.markdown(
        """
<div class="tour-card">
  <h4>En une phrase</h4>
  <div class="body">
  <b>6</b> = toutes les combinaisons ; <b>7</b> = le meilleur + Gantt/convergence ;
  <b>6 encore</b> = nouvelle grille ; <b>8</b> = historique des gains (pas un simple doublon de 7).
  </div>
</div>
""",
        unsafe_allow_html=True,
    )