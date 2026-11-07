# ==============================================================================
#  VeloFit AI Studio v3 — Laboratoire d'analyse posturale pour le vélo
#  Lancement :  streamlit run app.py
#  (la logique métier est dans velofit_core.py, à placer dans le même dossier)
# ==============================================================================
import hashlib
import os
import re
import tempfile
from datetime import datetime
from functools import partial
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import accounts as acc
import auth_ui
import velofit_core as core
from velofit_core import META, ORDER, STATUS

st.set_page_config(page_title="VeloFit AI — Studio Postural", page_icon="🚴", layout="wide", initial_sidebar_state="auto")

# ------------------------------------------------------------------------------
#  DESIGN
# ------------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--panel:rgba(15,22,38,.72);--line:rgba(148,163,184,.14);--txt:#e8edf6;--mut:#8a97ad;--cy:#22d3ee;--vi:#8b5cf6;--ok:#34d399;--warn:#fbbf24;--bad:#fb7185;}
html, body, .stApp{font-family:'Inter',-apple-system,sans-serif; color:var(--txt);}
.stApp{background:radial-gradient(1100px 560px at 8% -10%, rgba(34,211,238,.11), transparent 60%),radial-gradient(900px 520px at 100% 0%, rgba(139,92,246,.13), transparent 60%),#05070d;}
header[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer{visibility:hidden;}
.block-container{padding-top:1.8rem; max-width:1320px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1020 0%,#080c18 100%); border-right:1px solid var(--line);}
[data-testid="stSidebar"] h3{font-family:'Space Grotesk',sans-serif; font-size:1rem; letter-spacing:.02em; color:var(--cy);}
.side-sec{font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; color:var(--mut); margin:18px 0 6px;}
.hero{position:relative; overflow:hidden; border:1px solid var(--line); border-radius:26px; padding:34px 40px; margin-bottom:22px;
  background:linear-gradient(135deg, rgba(34,211,238,.09), rgba(139,92,246,.11)), var(--panel); -webkit-backdrop-filter:blur(14px); backdrop-filter:blur(14px);}
.hero::after{content:""; position:absolute; inset:0; pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);
  background-size:38px 38px; -webkit-mask-image:radial-gradient(circle at 85% 15%, #000, transparent 65%); mask-image:radial-gradient(circle at 85% 15%, #000, transparent 65%);}
.hero-badge{display:inline-flex; align-items:center; gap:8px; font-size:.74rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:var(--cy);
  border:1px solid rgba(34,211,238,.35); background:rgba(34,211,238,.08); padding:6px 12px; border-radius:999px; position:relative; z-index:1;}
.hero-badge i{width:7px; height:7px; border-radius:50%; background:var(--cy); animation:pulse 2s infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(34,211,238,.6)}70%{box-shadow:0 0 0 10px rgba(34,211,238,0)}100%{box-shadow:0 0 0 0 rgba(34,211,238,0)}}
.hero h1{font-family:'Space Grotesk',sans-serif; font-size:3rem; font-weight:700; line-height:1.05; margin:16px 0 10px; letter-spacing:-.03em; position:relative; z-index:1;
  background:linear-gradient(120deg,#fff 0%,#7dd3fc 45%,#a78bfa 100%); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;}
.hero p{max-width:760px; color:#9fb0c8; font-size:1.05rem; line-height:1.55; margin:0; position:relative; z-index:1;}
.glass{background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:22px; -webkit-backdrop-filter:blur(12px); backdrop-filter:blur(12px); box-shadow:0 18px 40px -20px rgba(0,0,0,.7);}
.feat{transition:transform .25s ease, border-color .25s ease; height:100%; margin-bottom:14px;}
.feat:hover{transform:translateY(-4px); border-color:rgba(34,211,238,.45);}
.feat .ico{font-size:1.6rem; margin-bottom:10px;}
.feat h4{font-family:'Space Grotesk',sans-serif; margin:0 0 6px; font-size:1.1rem; color:#fff;}
.feat p{margin:0; color:var(--mut); font-size:.92rem; line-height:1.5;}
.step{display:flex; gap:14px; align-items:flex-start; padding:14px 0; border-bottom:1px solid var(--line);}
.step:last-child{border-bottom:none;}
.step .n{flex:0 0 34px; height:34px; border-radius:10px; display:grid; place-items:center; font-weight:700; font-family:'Space Grotesk',sans-serif; color:#04101a; background:linear-gradient(135deg,var(--cy),#818cf8);}
.step b{color:#fff;} .step span{color:var(--mut); font-size:.92rem;}
.score-wrap{display:flex; gap:24px; align-items:center;}
.ring{--p:0; --c:var(--ok); flex:0 0 150px; width:150px; height:150px; border-radius:50%; background:conic-gradient(var(--c) calc(var(--p) * 1%), #18223a 0); display:grid; place-items:center; box-shadow:0 0 40px -8px var(--c);}
.ring-in{width:118px; height:118px; border-radius:50%; background:#0a0f1d; display:grid; place-items:center; text-align:center;}
.ring-val{font-family:'Space Grotesk',sans-serif; font-size:2.5rem; font-weight:700; line-height:1; color:#fff;}
.ring-sub{font-size:.7rem; color:var(--mut); letter-spacing:.1em;}
.verdict h3{font-family:'Space Grotesk',sans-serif; margin:0 0 4px; font-size:1.5rem; color:#fff;}
.verdict p{margin:0; color:var(--mut); font-size:.92rem; line-height:1.5;}
.chip{--c:var(--ok); display:inline-flex; align-items:center; gap:6px; font-size:.7rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--c);
  border:1px solid color-mix(in srgb, var(--c) 45%, transparent); background:color-mix(in srgb, var(--c) 12%, transparent); padding:4px 10px; border-radius:999px; white-space:nowrap;}
.chip::before{content:""; width:6px; height:6px; border-radius:50%; background:var(--c);}
.mcard{background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px 16px 12px; margin-bottom:12px; transition:border-color .2s ease, transform .2s ease;}
.mcard:hover{border-color:rgba(34,211,238,.4); transform:translateY(-2px);}
.mcard-top{display:flex; justify-content:space-between; align-items:center; gap:8px;}
.mcard-label{font-size:.82rem; font-weight:500; color:#b6c2d6;}
.mcard-value{font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:700; color:#fff; margin:6px 0 10px; line-height:1;}
.mcard-value small{font-size:1rem; color:var(--mut); margin-left:2px;}
.gauge{position:relative; height:8px; border-radius:99px; background:#18223a;}
.gauge-zone{position:absolute; top:0; bottom:0; border-radius:99px; background:linear-gradient(90deg, rgba(52,211,153,.35), rgba(52,211,153,.6));}
.gauge-mark{position:absolute; top:-4px; width:4px; height:16px; border-radius:3px; transform:translateX(-50%); box-shadow:0 0 12px var(--c); background:var(--c);}
.gauge-scale{display:flex; justify-content:space-between; font-size:.68rem; color:var(--mut); margin-top:8px;}
.insight{border:1px solid var(--line); border-left:4px solid var(--c); border-radius:14px; padding:16px 18px; margin:0 0 14px;
  background:linear-gradient(90deg, color-mix(in srgb, var(--c) 7%, transparent), transparent 60%), var(--panel);}
.insight-h{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:6px;}
.insight-h b{font-family:'Space Grotesk',sans-serif; font-size:1.05rem; color:#fff;}
.insight p{margin:4px 0 8px; color:#b3c0d4; font-size:.93rem; line-height:1.55;}
.insight ul{margin:0; padding-left:18px; color:#d6deec; font-size:.92rem; line-height:1.7;}
.why{color:#7dd3fc !important; font-size:.86rem !important;}
.prio{display:flex; gap:12px; align-items:center; padding:12px 14px; border:1px solid var(--line); border-radius:12px; margin-bottom:8px; background:var(--panel);}
.prio .num{width:28px; height:28px; border-radius:8px; display:grid; place-items:center; font-weight:700; color:#04101a; background:var(--c);}
.prio .t{flex:1; font-size:.92rem;} .prio .t b{color:#fff;}
.note{font-size:.78rem; color:var(--mut); line-height:1.5; border:1px dashed var(--line); border-radius:12px; padding:10px 14px; margin-top:10px;}
.stTabs [data-baseweb="tab-list"]{gap:8px; border-bottom:none; flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:9px 16px; color:var(--mut); font-weight:500;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#0891b2 0%,#6d28d9 100%) !important; color:#fff !important; border-color:rgba(34,211,238,.6) !important; box-shadow:0 8px 24px -10px rgba(34,211,238,.6);}
[data-testid="stFileUploader"] section{background:var(--panel); border:1.5px dashed rgba(34,211,238,.35); border-radius:18px; padding:22px;}
.stButton>button, .stDownloadButton>button{border-radius:12px; border:1px solid rgba(34,211,238,.4); background:linear-gradient(135deg,rgba(8,145,178,.25),rgba(109,40,217,.25)); color:#fff; font-weight:600; transition:all .2s ease;}
.stButton>button:hover, .stDownloadButton>button:hover{border-color:var(--cy); box-shadow:0 8px 24px -10px rgba(34,211,238,.7); transform:translateY(-1px);}
[data-testid="stMetric"]{background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px;}

/* ---- Thème sombre forcé, même si le téléphone est en mode clair ---- */
:root{color-scheme:dark;}
html{-webkit-text-size-adjust:100%;}
.stApp{color-scheme:dark; overflow-x:hidden;}
.stApp .stMarkdown, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stWidgetLabel"] label, .stApp label p, .stApp [data-testid="stCaptionContainer"]{color:var(--txt);}
.stApp [data-testid="stCaptionContainer"]{color:var(--mut);}

/* ---- Couleurs de repli si le navigateur ne gère pas color-mix() ---- */
.chip{border:1px solid var(--c); background:rgba(255,255,255,.06);}
.insight{background:var(--panel);}
@supports (color: color-mix(in srgb, red 50%, blue)){
  .chip{border:1px solid color-mix(in srgb, var(--c) 45%, transparent); background:color-mix(in srgb, var(--c) 12%, transparent);}
  .insight{background:linear-gradient(90deg, color-mix(in srgb, var(--c) 7%, transparent), transparent 60%), var(--panel);}
}

/* ---- Téléphone ---- */
@media (max-width: 640px){
  .block-container{padding:3.2rem .85rem 3rem;}
  .hero{padding:22px 18px; border-radius:20px; margin-bottom:16px;}
  .hero h1{font-size:2.05rem; margin:12px 0 8px;}
  .hero p{font-size:.94rem;}
  .hero-badge{font-size:.66rem; padding:5px 10px;}
  .glass{padding:16px; border-radius:16px;}
  .feat h4{font-size:1rem;}
  .score-wrap{flex-direction:column; text-align:center; gap:14px;}
  .ring{flex:0 0 auto; width:132px; height:132px;}
  .ring-in{width:102px; height:102px;}
  .ring-val{font-size:2.1rem;}
  .verdict h3{font-size:1.25rem;}
  .mcard{padding:12px 14px 10px;}
  .mcard-top{flex-wrap:wrap; gap:6px;}
  .mcard-value{font-size:1.7rem;}
  .insight{padding:13px 14px;}
  .insight-h b{font-size:1rem;}
  .prio{flex-wrap:wrap; gap:8px;}
  .stTabs [data-baseweb="tab-list"]{flex-wrap:nowrap; overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none;}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{display:none;}
  .stTabs [data-baseweb="tab"]{padding:8px 12px; white-space:nowrap; flex:0 0 auto; font-size:.88rem;}
  [data-testid="stFileUploader"] section{padding:14px;}
  [data-testid="stMetric"]{padding:10px;}
  .step{padding:10px 0;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def H(html: str):
    """Affiche du HTML en supprimant les sauts de ligne (évite les blocs « code » de Markdown)."""
    st.markdown(re.sub(r"\s*\n\s*", " ", html.strip()), unsafe_allow_html=True)


def stretch(fn, *args, **kwargs):
    """Compatibilité entre versions de Streamlit pour l'affichage pleine largeur."""
    last = None
    for opt in ({"width": "stretch"}, {"use_container_width": True}, {}):
        try:
            return fn(*args, **kwargs, **opt)
        except TypeError as exc:
            last = exc
        except Exception as exc:  # largeur refusée par une ancienne version
            last = exc
    raise last


def note(txt):
    H(f'<div class="note">{txt}</div>')


# ------------------------------------------------------------------------------
#  CONNEXION OBLIGATOIRE ET STOCKAGE ISOLÉ PAR COMPTE
# ------------------------------------------------------------------------------
user = auth_ui.gate()            # affiche la page de connexion et arrête le script si besoin
SC = user["username"]
IS_ADMIN = user["role"] == "admin"
_STORE_FNS = ("list_profiles", "load_profile", "save_profile", "load_history", "add_history", "update_history_entry",
              "delete_history_entry", "load_history_image", "profile_summary")
store = SimpleNamespace(**{n: partial(getattr(core, n), scope=SC) for n in _STORE_FNS})


# ------------------------------------------------------------------------------
#  ÉTAT, PROFILS
# ------------------------------------------------------------------------------
DEFAULTS = dict(height=175, inseam=0, shoulder_w=0, flex="Moyenne", discipline="Route / Endurance", goal="Équilibré",
                side_choice="Auto", complaints=[], target_score=85, use_mob=False, learn=True, show_grid=False,
                mode="Cycliste", profile_name="Invité", studio="", logo_png=None)
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)
for _t in core.MOBILITY_TESTS:
    st.session_state.setdefault("mob_" + _t["key"], _t["options"][len(_t["options"]) // 2])

PROFILE_KEYS = ["height", "inseam", "shoulder_w", "flex", "discipline", "goal", "target_score", "use_mob", "complaints"] + \
               ["mob_" + t["key"] for t in core.MOBILITY_TESTS]
NEW_LABEL = "➕ Nouveau profil"


def _load_profile_cb():
    sel = st.session_state.get("profile_sel", NEW_LABEL)
    if sel == NEW_LABEL:
        return
    p = store.load_profile(sel)
    st.session_state["profile_name"] = sel
    for k in PROFILE_KEYS:
        if k in p:
            st.session_state[k] = p[k]
    if st.session_state["discipline"] not in core.BASE_RANGES:
        st.session_state["discipline"] = DEFAULTS["discipline"]
    st.session_state["complaints"] = [c for c in st.session_state["complaints"] if c in core.COMPLAINTS]


def mobility_answers():
    ans = {}
    for t in core.MOBILITY_TESTS:
        v = st.session_state.get("mob_" + t["key"], t["options"][len(t["options"]) // 2])
        ans[t["key"]] = t["options"].index(v) if v in t["options"] else len(t["options"]) // 2
    return ans


# ------------------------------------------------------------------------------
#  BARRE LATÉRALE
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🚴 VeloFit AI")
    auth_ui.sidebar_box(user)
    st.divider()
    st.radio("Mode d'utilisation", ["Cycliste", "Fitter (professionnel)"], key="mode", horizontal=False,
             help="Le mode Fitter gère plusieurs clients, personnalise les rapports (logo, nom du studio) et affiche un tableau de bord.")
    fitter = st.session_state["mode"].startswith("Fitter")
    who = "client" if fitter else "profil"

    st.markdown(f'<div class="side-sec">{"Client" if fitter else "Profil"}</div>', unsafe_allow_html=True)
    _profiles = store.list_profiles()
    st.selectbox(f"Ouvrir un {who} existant", [NEW_LABEL] + _profiles, key="profile_sel", on_change=_load_profile_cb)
    st.text_input(f"Nom du {who}", key="profile_name")
    active = (st.session_state["profile_name"] or "").strip() or "Invité"

    st.markdown('<div class="side-sec">Morphologie</div>', unsafe_allow_html=True)
    st.number_input("Taille (cm)", 140, 215, step=1, key="height")
    st.number_input("Entrejambe (cm) — optionnel", 0, 110, step=1, key="inseam", help="0 = non renseigné. Sert aux formules de hauteur de selle et à la longueur de manivelle.")
    st.number_input("Largeur d'épaules (cm) — optionnel", 0, 60, step=1, key="shoulder_w", help="Distance entre les deux points osseux des épaules. Sert à la largeur de cintre.")
    st.select_slider("Souplesse (ischios / dos)", ["Limitée", "Moyenne", "Très souple"], key="flex")
    st.checkbox("Affiner avec le questionnaire de mobilité", key="use_mob", help="Remplit les tests dans l'onglet « Mobilité & douleurs ». Les plages cibles s'adaptent à vos résultats.")

    st.markdown('<div class="side-sec">Pratique</div>', unsafe_allow_html=True)
    st.selectbox("Discipline", list(core.BASE_RANGES.keys()), key="discipline")
    st.select_slider("Objectif", ["Confort", "Équilibré", "Performance"], key="goal")
    st.slider("Score visé", 50, 100, step=5, key="target_score")

    st.markdown('<div class="side-sec">Prise de vue</div>', unsafe_allow_html=True)
    st.radio("Côté visible", ["Auto", "Droit", "Gauche"], horizontal=True, key="side_choice")
    st.checkbox("Grille de cadrage sur l'image", key="show_grid")

    st.markdown('<div class="side-sec">Douleurs ressenties</div>', unsafe_allow_html=True)
    st.multiselect("Sélectionnez", list(core.COMPLAINTS.keys()), key="complaints", label_visibility="collapsed")

    st.markdown('<div class="side-sec">Options</div>', unsafe_allow_html=True)
    st.checkbox("Explications pédagogiques", key="learn", help="Affiche pourquoi chaque angle compte (idéal pour débuter).")
    if st.button(f"💾 Enregistrer le {who}"):
        store.save_profile(active, {k: st.session_state[k] for k in PROFILE_KEYS})
        st.success("Profil enregistré.")
    with st.expander("🎯 Protocole rapide"):
        st.markdown("- Profil strict, côté de la jambe mesurée\n- Vélo sur home-trainer\n- Photo : manivelle au **point mort bas** (6 h)\n- Vidéo : 10 à 15 s de pédalage régulier\n- Appareil à hauteur de hanche, ~3 m")

ss = st.session_state
ctx_flex = ss["flex"]
extra_shift = {}
mob = None
if ss["use_mob"]:
    mob = core.mobility_profile(mobility_answers())
    ctx_flex = mob["flex_label"]
    extra_shift = mob["shifts"]
ranges = core.get_ranges(ss["discipline"], ctx_flex, ss["goal"], extra_shift)
ctx = dict(height=int(ss["height"]), inseam=int(ss["inseam"]), flex=ctx_flex, discipline=ss["discipline"], goal=ss["goal"])

# ------------------------------------------------------------------------------
#  COMPOSANTS D'INTERFACE
# ------------------------------------------------------------------------------
def metric_card(key, value, ev, rng):
    meta = META[key]
    color, label = STATUS[ev["status"]]
    span = meta["vmax"] - meta["vmin"]
    pos = max(0, min(100, (value - meta["vmin"]) / span * 100))
    z0 = max(0, min(100, (rng[0] - meta["vmin"]) / span * 100))
    z1 = max(0, min(100, (rng[1] - meta["vmin"]) / span * 100))
    H(f"""
    <div class="mcard" style="--c:{color}">
      <div class="mcard-top"><span class="mcard-label">{meta['icon']} {meta['label']}</span><span class="chip" style="--c:{color}">{label}</span></div>
      <div class="mcard-value">{value:.1f}<small>°</small></div>
      <div class="gauge"><div class="gauge-zone" style="left:{z0}%;width:{z1 - z0}%"></div><div class="gauge-mark" style="left:{pos}%"></div></div>
      <div class="gauge-scale"><span>{meta['vmin']}°</span><span>cible {rng[0]}–{rng[1]}°</span><span>{meta['vmax']}°</span></div>
    </div>""")


def card(status, title, body, actions=None, tag=None, why=None):
    color, label = STATUS[status]
    ul = "<ul>" + "".join(f"<li>{a}</li>" for a in actions) + "</ul>" if actions else ""
    wy = f'<p class="why">💡 {why}</p>' if why and ss["learn"] else ""
    H(f'<div class="insight" style="--c:{color}"><div class="insight-h"><span class="chip" style="--c:{color}">{tag or label}</span><b>{title}</b></div>'
      f"<p>{body}</p>{wy}{ul}</div>")


def insight(rec):
    card(rec["status"], rec["title"], rec["diag"], rec["actions"], why=rec.get("why"))


def score_ring(score):
    color = "#34d399" if score >= 80 else ("#fbbf24" if score >= 60 else "#fb7185")
    title, sub = core.verdict_for(score)
    H(f"""
    <div class="score-wrap">
      <div class="ring" style="--p:{score:.0f};--c:{color}"><div class="ring-in"><div><div class="ring-val">{score:.0f}</div><div class="ring-sub">/ 100</div></div></div></div>
      <div class="verdict"><h3>{title}</h3><p>{sub}</p></div>
    </div>""")


def radar(scores, title_b="Votre position", scores_b=None):
    labels = [META[k]["short"] for k in ORDER]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[100] * (len(ORDER) + 1), theta=labels + [labels[0]], mode="lines",
                                  line=dict(color="rgba(52,211,153,.35)", dash="dot"), hoverinfo="skip", name="Idéal"))
    if scores_b is not None:
        vb = [scores_b[k] for k in ORDER]
        fig.add_trace(go.Scatterpolar(r=vb + [vb[0]], theta=labels + [labels[0]], fill="toself", name=title_b,
                                      line=dict(color="#a78bfa", width=2), fillcolor="rgba(167,139,250,.15)"))
    vals = [scores[k] for k in ORDER]
    fig.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill="toself", name="Actuel" if scores_b is not None else title_b,
                                  line=dict(color="#22d3ee", width=3), fillcolor="rgba(34,211,238,.22)"))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="rgba(148,163,184,.18)", tickfont=dict(color="#8a97ad", size=9)),
                                 angularaxis=dict(gridcolor="rgba(148,163,184,.18)", tickfont=dict(color="#cbd5e1", size=11))),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=scores_b is not None, legend=dict(font=dict(color="#cbd5e1")),
                      margin=dict(l=40, r=40, t=20, b=20), height=340, font=dict(family="Inter"))
    return fig


def line_fig(x, series, height=300, target=None, ytitle=""):
    fig = go.Figure()
    for name, y, color in series:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(color=color, width=3), marker=dict(size=8)))
    if target is not None:
        fig.add_hline(y=target, line_dash="dot", line_color="#34d399", annotation_text="objectif", annotation_font_color="#34d399")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height, margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(family="Inter", color="#cbd5e1"), xaxis=dict(gridcolor="rgba(148,163,184,.12)"),
                      yaxis=dict(gridcolor="rgba(148,163,184,.12)", title=ytitle), legend=dict(orientation="h", y=1.12))
    return fig


def landing():
    feats = [
        ("🎞️", "Photo, vidéo ou caméra", "Analyse statique au point mort bas ou dynamique sur 10 s de pédalage : cadence, régularité, amplitude du genou."),
        ("🎯", "Score postural /100", "Six angles pondérés, un radar et un plan d'action priorisé et chiffré en millimètres."),
        ("📏", "Calibration", "Échelle automatique selon votre taille ou manuelle avec une longueur connue : vos réglages en vrais mm."),
        ("🧭", "Recul de selle & vue de face", "Position du genou par rapport à l'axe de pédale (KOPS), symétrie du bassin et alignement des genoux."),
        ("🧘", "Mobilité & douleurs", "Questionnaire de souplesse qui adapte les cibles, et mise en relation de vos douleurs avec les mesures."),
        ("🔁", "Suivi & transfert", "Historique par profil, comparaison avant/après, objectif de score et transfert des réglages d'un vélo à un autre."),
    ]
    for row in (feats[:3], feats[3:]):
        cols = st.columns(3, gap="medium")
        for c, (ico, t, d) in zip(cols, row):
            with c:
                H(f'<div class="glass feat"><div class="ico">{ico}</div><h4>{t}</h4><p>{d}</p></div>')
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        H("""
        <div class="glass"><h4 style="font-family:'Space Grotesk';margin:0 0 6px;color:#fff;">Protocole d'acquisition</h4>
          <div class="step"><div class="n">1</div><div><b>Vélo stabilisé</b><br><span>Montez-le sur un home-trainer, position de pédalage naturelle.</span></div></div>
          <div class="step"><div class="n">2</div><div><b>Profil strict</b><br><span>Appareil à hauteur de hanche, à 3 m, perpendiculaire au vélo.</span></div></div>
          <div class="step"><div class="n">3</div><div><b>Photo ou vidéo</b><br><span>Photo à 6 h (point mort bas) ou 10 à 15 s de pédalage régulier.</span></div></div>
          <div class="step"><div class="n">4</div><div><b>Tenue ajustée</b><br><span>Vêtements près du corps et contrastés, bon éclairage, corps entier cadré.</span></div></div>
        </div>""")
    with right:
        H("""
        <div class="glass"><h4 style="font-family:'Space Grotesk';margin:0 0 10px;color:#fff;">Ce que nous mesurons</h4>
          <p style="color:#8a97ad;font-size:.92rem;line-height:1.6;margin:0 0 12px;">Six angles biomécaniques sont comparés à des plages cibles adaptées à votre discipline, votre souplesse et votre objectif.</p>
          <span class="chip" style="--c:#22d3ee">Genou</span> <span class="chip" style="--c:#8b5cf6">Tronc</span> <span class="chip" style="--c:#22d3ee">Hanche</span>
          <span class="chip" style="--c:#8b5cf6">Épaule</span> <span class="chip" style="--c:#22d3ee">Coude</span> <span class="chip" style="--c:#8b5cf6">Cheville</span>
        </div>""")


def glossary():
    for term, text in core.GLOSSARY_TERMS:
        with st.expander(term):
            st.write(text)


# ------------------------------------------------------------------------------
#  SUIVI ET COMPARAISON (utilisé aussi avant l'analyse)
# ------------------------------------------------------------------------------
def history_section(name, current=None, kp=""):
    """current : dict(m, score, annotated, source, quality, extra) pour proposer l'enregistrement."""
    hist = store.load_history(name)
    if current is not None:
        c1, c2 = st.columns([2, 1])
        label = c1.text_input("Nom de cette analyse", value=f"Analyse {len(hist) + 1}", key=f"{kp}hist_label")
        note_txt = st.text_input("Réglage modifié depuis la précédente (facultatif)", placeholder="ex. selle montée de 5 mm", key=f"{kp}hist_note")
        c2.write("")
        c2.write("")
        if c2.button("💾 Enregistrer", key=f"{kp}save_hist"):
            entry = dict(label=label, note=note_txt, score=round(current["score"], 1), source=current["source"], discipline=ss["discipline"],
                         goal=ss["goal"], quality=round(current["quality"], 1), m={k: round(v, 2) for k, v in current["m"].items()},
                         ev={k: current["ev"][k]["status"] for k in ORDER}, **current.get("extra", {}))
            store.add_history(name, entry, core.png_bytes(current["annotated"]))
            if not (name == "Invité" and name not in store.list_profiles()):
                store.save_profile(name, {k: st.session_state[k] for k in PROFILE_KEYS})
            st.success("Analyse enregistrée dans l'historique.")
            hist = store.load_history(name)
    if not hist:
        st.caption("Aucune analyse enregistrée pour ce profil. Enregistrez vos analyses pour comparer l'avant / après de vos réglages.")
        return
    summary = store.profile_summary(name)
    dates = [e["date"][:10] + " " + e["date"][11:16] for e in hist]
    scores = [e["score"] for e in hist]
    best = max(scores)
    a, b, c = st.columns(3)
    a.metric("Analyses", len(hist))
    b.metric("Dernier score", f"{scores[-1]:.0f}", f"{scores[-1] - scores[0]:+.0f} depuis la 1re" if len(hist) > 1 else None)
    c.metric("Meilleur score", f"{best:.0f}")
    tgt = ss["target_score"]
    st.progress(min(1.0, scores[-1] / tgt), text=f"Progression vers l'objectif de {tgt}/100 : {min(100, scores[-1] / tgt * 100):.0f} %")
    if len(hist) > 1:
        stretch(st.plotly_chart, line_fig(dates, [("Score", scores, "#22d3ee")], target=tgt, ytitle="Score /100"))
    rows = []
    for e in hist:
        r = {"Analyse": e.get("label", ""), "Date": e["date"][:16].replace("T", " "), "Source": e.get("source", ""), "Score": e["score"], "Réglage": e.get("note", "")}
        for k in ORDER:
            r[META[k]["short"]] = e["m"].get(k)
        if e.get("avg_power"):
            r["Puissance moy. (W)"] = round(e["avg_power"])
        rows.append(r)
    stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)

    if len(hist) >= 2:
        st.markdown("##### Comparer deux analyses")
        opts = {f"{e.get('label', '')} · {e['date'][:16].replace('T', ' ')} · {e['score']:.0f}/100": e for e in hist}
        names = list(opts.keys())
        ca, cb = st.columns(2)
        ea = opts[ca.selectbox("Avant", names, index=max(0, len(names) - 2), key=f"{kp}cmp_a")]
        eb = opts[cb.selectbox("Après", names, index=len(names) - 1, key=f"{kp}cmp_b")]
        ia, ib = store.load_history_image(name, ea), store.load_history_image(name, eb)
        i1, i2 = st.columns(2)
        if ia:
            stretch(i1.image, ia, caption=f"Avant — {ea['score']:.0f}/100")
        if ib:
            stretch(i2.image, ib, caption=f"Après — {eb['score']:.0f}/100")
        d1, d2, d3 = st.columns(3)
        d1.metric("Score", f"{eb['score']:.0f}", f"{eb['score'] - ea['score']:+.1f}")
        rows = []
        for k in ORDER:
            va, vb = ea["m"].get(k), eb["m"].get(k)
            if va is None or vb is None:
                continue
            rows.append({"Mesure": META[k]["label"], "Avant": round(va, 1), "Après": round(vb, 1), "Variation": round(vb - va, 1),
                         "Statut avant": STATUS[ea.get("ev", {}).get(k, "ok")][1] if ea.get("ev") else "", "Statut après": STATUS[eb.get("ev", {}).get(k, "ok")][1] if eb.get("ev") else ""})
        stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)
        if eb.get("note"):
            st.caption(f"Réglage noté pour l'analyse « Après » : {eb['note']}")

    st.markdown("##### Données de sortie (puissance, fréquence cardiaque)")
    st.caption("Importez l'export CSV d'une sortie pour l'associer à une analyse et suivre le lien entre position et performance.")
    csv = st.file_uploader("Export CSV (colonnes power / watts et heart rate / bpm)", type=["csv"], key=f"{kp}ride_csv")
    if csv is not None:
        try:
            stats = core.parse_ride_csv(pd.read_csv(csv, sep=None, engine="python"))
        except Exception:
            stats = None
            st.error("Impossible de lire ce CSV.")
        if stats:
            if stats["avg_power"] is None and stats["avg_hr"] is None:
                st.warning("Aucune colonne de puissance ou de fréquence cardiaque reconnue.")
            else:
                st.write(f"Puissance moyenne : **{stats['avg_power']:.0f} W**" if stats["avg_power"] else "Puissance : non trouvée.")
                if stats["avg_hr"]:
                    st.write(f"Fréquence cardiaque moyenne : **{stats['avg_hr']:.0f} bpm**")
                all_opts = {f"{e.get('label', '')} · {e['date'][:16].replace('T', ' ')} · {e['score']:.0f}/100": e for e in hist}
                target = st.selectbox("Associer à l'analyse", list(all_opts.keys()), index=len(all_opts) - 1, key=f"{kp}csv_target")
                if target and st.button("Associer", key=f"{kp}assoc_csv"):
                    upd = {}
                    if stats["avg_power"]:
                        upd["avg_power"] = stats["avg_power"]
                    if stats["avg_hr"]:
                        upd["avg_hr"] = stats["avg_hr"]
                    store.update_history_entry(name, all_opts[target]["id"], upd)
                    st.success("Données associées. Rechargez l'historique pour les voir.")
    pw = [(e["score"], e["avg_power"], e.get("label", "")) for e in hist if e.get("avg_power")]
    if len(pw) >= 2:
        fig = go.Figure(go.Scatter(x=[p[0] for p in pw], y=[p[1] for p in pw], mode="markers+text", text=[p[2] for p in pw], textposition="top center",
                                   marker=dict(size=12, color="#22d3ee")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280, margin=dict(l=10, r=10, t=10, b=10), font=dict(color="#cbd5e1"),
                          xaxis=dict(title="Score postural", gridcolor="rgba(148,163,184,.12)"), yaxis=dict(title="Puissance moyenne (W)", gridcolor="rgba(148,163,184,.12)"))
        stretch(st.plotly_chart, fig)
        note("Ce graphique montre la relation entre votre score postural et la puissance moyenne de sorties associées. Il est indicatif : la forme du jour, le parcours et la fatigue jouent aussi.")
    with st.expander("🗑️ Supprimer une analyse"):
        opts_del = {f"{e.get('label', '')} · {e['date'][:16].replace('T', ' ')}": e["id"] for e in hist}
        pick = st.selectbox("Analyse à supprimer", list(opts_del.keys()), key=f"{kp}del_pick")
        if st.button("Supprimer définitivement", key=f"{kp}del_btn"):
            store.delete_history_entry(name, opts_del[pick])
            st.rerun()


# ------------------------------------------------------------------------------
#  EN-TÊTE ET SOURCE DE L'IMAGE
# ------------------------------------------------------------------------------
brand = (ss["studio"] or "VeloFit AI Studio") if fitter else "VeloFit AI Studio"
H(f"""
<div class="hero">
  <span class="hero-badge"><i></i>Analyse biomécanique par IA</span>
  <h1>{brand}</h1>
  <p>Votre laboratoire virtuel de bike-fitting : photo ou vidéo de pédalage, six angles mesurés, un score postural, un plan d'action chiffré, un simulateur de réglages et un suivi dans le temps.</p>
</div>""")

source = st.radio("Source", ["📂 Photo", "🎬 Vidéo de pédalage", "📷 Caméra"], horizontal=True, label_visibility="collapsed")
photo_bytes = video_bytes = None
if source.startswith("📂"):
    up = st.file_uploader("Vue de profil (JPG ou PNG)", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    photo_bytes = up.getvalue() if up is not None else None
elif source.startswith("🎬"):
    up = st.file_uploader("Vidéo de profil (MP4, MOV, AVI) — 10 à 15 s de pédalage régulier", type=["mp4", "mov", "avi", "m4v"], label_visibility="collapsed")
    video_bytes = up.getvalue() if up is not None else None
else:
    up = st.camera_input("Photo de profil", label_visibility="collapsed")
    photo_bytes = up.getvalue() if up is not None else None

_top_names = ["🏠 Analyse", "📈 Suivi & historique", "🧑‍🏫 Clients" if fitter else "📘 Guide"] + (["🛠️ Administration"] if IS_ADMIN else [])
tabs_top = st.tabs(_top_names)
t_main, t_hist_top, t_third = tabs_top[:3]
t_admin = tabs_top[3] if IS_ADMIN else None

with t_hist_top:
    history_section(active, kp="top_")

with t_third:
    if fitter:
        profs = store.list_profiles()
        if not profs:
            st.info("Aucun client enregistré. Saisissez un nom dans la barre latérale puis enregistrez le profil.")
        else:
            rows = []
            for p in profs:
                s = store.profile_summary(p)
                rows.append({"Client": p, "Analyses": s["n"], "Dernier score": s["last_score"], "Dernière visite": s["last_date"], "Discipline": s["discipline"], "Objectif": s["target"]})
            stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)
            note("Ouvrez un client avec la liste « Ouvrir un client existant » dans la barre latérale.")
        st.markdown("##### Image de marque des rapports")
        ss["studio"] = st.text_input("Nom du studio", value=ss["studio"], placeholder="ex. Cycles Dupont — Studio de fitting", key="studio_in")
        logo = st.file_uploader("Logo (PNG ou JPG)", type=["png", "jpg", "jpeg"], key="logo_up")
        if logo is not None:
            ss["logo_png"] = logo.getvalue()
        if ss["logo_png"]:
            st.image(ss["logo_png"], width=140)
    else:
        st.markdown("##### Glossaire")
        glossary()
        st.markdown(f"##### Conseils pour la discipline « {ss['discipline']} »")
        for tip in core.DISCIPLINE_TIPS[ss["discipline"]]:
            st.markdown(f"- {tip}")

if IS_ADMIN:
    with t_admin:
        auth_ui.admin_panel(user)

# ------------------------------------------------------------------------------
#  ANALYSE
# ------------------------------------------------------------------------------
with t_main:
    if photo_bytes is None and video_bytes is None:
        st.session_state["_analysis"] = None
        st.write("")
        landing()
        st.stop()

    # --- quota : une analyse est décomptée une seule fois par fichier et par compte
    _raw = video_bytes if video_bytes is not None else photo_bytes
    _ok, _why, _charged = acc.use_analysis(SC, hashlib.md5(_raw).hexdigest(), "vidéo" if video_bytes is not None else "photo")
    if not _ok:
        if _why == "quota":
            auth_ui.paywall(acc.get_user(SC))
        else:
            st.error("Votre compte n'est plus actif. Reconnectez-vous.")
        st.stop()
    if _charged and not IS_ADMIN:
        st.rerun()  # rafraîchit le compteur affiché dans la barre latérale

    A = {}
    try:
        if video_bytes is not None:
            key = hashlib.md5(video_bytes).hexdigest() + ss["side_choice"]
            if ss.get("_video_key") != key:
                suffix = ".mp4"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(video_bytes)
                    vpath = tmp.name
                bar = st.progress(0.0, text="Analyse de la vidéo…")
                try:
                    res = core.analyze_video(vpath, ss["side_choice"], progress=lambda f, t: bar.progress(f, text=f"Analyse de la vidéo… {t}"))
                finally:
                    bar.empty()
                    try:
                        os.unlink(vpath)
                    except OSError:
                        pass
                ss["_video_key"], ss["_video_res"] = key, res
            res = ss["_video_res"]
            if "error" in res:
                st.error("❌ " + res["error"])
                st.stop()
            lms = [tuple(x) for x in res["lms_best"]]
            A.update(img=res["image"], lms=lms, side=res["side"], m=res["m"], source="vidéo", video=res)
        else:
            with st.spinner("Détection du squelette et calcul des angles…"):
                det = core.detect_image(photo_bytes)
            if det is None:
                st.error("❌ Impossible de détecter un corps sur cette image. Importez une vue latérale nette, bien éclairée et entièrement cadrée.")
                st.stop()
            lms = det["landmarks"]
            side = core.auto_side(lms) if ss["side_choice"] == "Auto" else ss["side_choice"]
            A.update(img=det["image"], lms=lms, side=side, source="photo" if source.startswith("📂") else "caméra", video=None)
    except RuntimeError as exc:
        st.error(f"❌ {exc}")
        st.stop()

    img = A["img"]
    ih, iw = img.shape[:2]
    pts, vis = core.side_points(A["lms"], A["side"], iw, ih)
    m = A.get("m") or core.compute_metrics(pts)
    if A["video"] is None:
        m = core.compute_metrics(pts)
    ev = core.evaluate_all(m, ranges)
    scores = {k: ev[k]["score"] for k in ORDER}
    gscore = core.global_score(ev)

    # --- calibration
    cal_mode = ss.get("cal_mode", "Automatique (taille)")
    scale_auto = core.auto_scale(pts, ctx["height"])
    measured = None
    scale = scale_auto
    cal_info = "Échelle estimée à partir de votre taille."
    if cal_mode.startswith("Manuelle"):
        p1 = (ss.get("cal_x1", 10) / 100 * iw, ss.get("cal_y1", 50) / 100 * ih)
        p2 = (ss.get("cal_x2", 90) / 100 * iw, ss.get("cal_y2", 50) / 100 * ih)
        L_cm = float(ss.get("cal_len", 100.0))
        if np.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 5 and L_cm > 0:
            scale = core.manual_scale(p1, p2, L_cm)
            measured = (np.hypot(pts["hip"][0] - pts["knee"][0], pts["hip"][1] - pts["knee"][1]) / scale,
                        np.hypot(pts["knee"][0] - pts["ankle"][0], pts["knee"][1] - pts["ankle"][1]) / scale)
            cal_info = f"Échelle calibrée sur une longueur de {L_cm:g} cm."
    seg = core.leg_segments_mm(ctx["height"], measured)
    if measured is not None and seg != measured:
        cal_info += " Les segments mesurés semblent incohérents avec votre taille : le modèle anthropométrique est utilisé à la place (placez les points plus précisément)."
    ctx["seg"] = seg

    quality, qnotes, leg_tilt = core.assess_quality(A["lms"], vis, pts, iw, ih, img)
    recs = core.build_recommendations(m, ev, ranges, ctx)
    annotated = core.annotate(img, pts, m, ev, grid=ss["show_grid"])
    extras = []
    st.session_state["_analysis"] = True

    # --- tableau de bord principal
    col_img, col_side = st.columns([1.15, 0.85], gap="large")
    with col_img:
        st.markdown("#### 🔍 Analyse cinématique")
        stretch(st.image, annotated, caption=f"Côté analysé : {A['side']} · {ss['discipline']} · source : {A['source']}")
        qcol = "#34d399" if quality >= 75 else ("#fbbf24" if quality >= 55 else "#fb7185")
        H(f'<span class="chip" style="--c:{qcol}">Qualité de la prise de vue : {quality:.0f}/100</span>')
        with st.expander("📏 Calibration (optionnelle)"):
            st.caption(cal_info)
            st.radio("Mode", ["Automatique (taille)", "Manuelle (longueur connue)"], key="cal_mode", horizontal=True)
            if ss.get("cal_mode", "").startswith("Manuelle"):
                st.caption("Placez deux points sur un objet de longueur connue (ex. empattement, mètre ruban, hauteur de selle) dans le même plan que le cycliste, puis indiquez sa longueur.")
                s1, s2 = st.columns(2)
                s1.slider("Point 1 — x (%)", 0, 100, 10, key="cal_x1")
                s1.slider("Point 1 — y (%)", 0, 100, 50, key="cal_y1")
                s2.slider("Point 2 — x (%)", 0, 100, 90, key="cal_x2")
                s2.slider("Point 2 — y (%)", 0, 100, 50, key="cal_y2")
                st.number_input("Longueur réelle entre les deux points (cm)", 5.0, 400.0, 100.0, 0.5, key="cal_len")
                stretch(st.image, core.draw_calibration(img, (ss["cal_x1"] / 100 * iw, ss["cal_y1"] / 100 * ih), (ss["cal_x2"] / 100 * iw, ss["cal_y2"] / 100 * ih), f"{ss['cal_len']:g} cm"))
            segs = core.segments_mm(pts, scale)
            st.write("Segments estimés (mm) : " + " · ".join(f"{k} {v:.0f}" for k, v in segs.items()))
    with col_side:
        st.markdown("#### 🎯 Score postural")
        H('<div class="glass">')
        score_ring(gscore)
        H("</div>")
        st.write("")
        c1, c2 = st.columns(2)
        for i, k in enumerate(ORDER):
            with (c1 if i % 2 == 0 else c2):
                metric_card(k, m[k], ev[k], ranges[k])

    st.write("")
    names_tabs = ["🧭 Synthèse", "🚲 Selle & recul", "📐 Tronc & cockpit", "👟 Cales & matériel", "↔️ Vue de face", "🎬 Pédalage",
                  "🧘 Mobilité & douleurs", "🧪 Simulateur", "🔁 Transfert", "💾 Suivi", "📄 Rapport"]
    (t_syn, t_sel, t_tro, t_mat, t_front, t_ped, t_mob, t_sim, t_tr, t_follow, t_rep) = st.tabs(names_tabs)

    # --- synthèse
    with t_syn:
        a, b = st.columns([0.9, 1.1], gap="large")
        with a:
            st.markdown("##### Profil postural")
            stretch(st.plotly_chart, radar(scores))
            st.markdown("##### Fiabilité de la mesure")
            for lvl, txt in qnotes:
                H(f'<div class="insight" style="--c:{STATUS[lvl][0]}"><p style="margin:0">{txt}</p></div>')
        with b:
            st.markdown("##### Plan d'action priorisé")
            todo = sorted([r for r in recs if r["status"] != "ok"], key=lambda r: (0 if r["status"] == "bad" else 1, -META[r["key"]]["w"]))
            if not todo:
                card("ok", "Aucun réglage prioritaire", "Tous les angles sont dans les plages cibles. Conservez votre configuration et refaites un contrôle après tout changement de matériel.")
            for i, r in enumerate(todo, 1):
                c = STATUS[r["status"]][0]
                H(f'<div class="prio" style="--c:{c}"><div class="num">{i}</div><div class="t"><b>{r["title"]}</b><br>'
                  f'<span style="color:#8a97ad">{META[r["key"]]["label"]} · {m[r["key"]]:.1f}°</span></div><span class="chip" style="--c:{c}">{STATUS[r["status"]][1]}</span></div>')
            if todo:
                st.caption("Corrigez un paramètre à la fois, dans cet ordre, puis refaites une analyse pour valider.")
            if ss["learn"]:
                with st.expander("📘 Comment lire ces résultats ?"):
                    st.write("Chaque angle est comparé à une plage cible. En vert : dans la cible. En orange : écart modéré. En rouge : écart important. Le score est une moyenne pondérée : le genou compte le plus (30 %), car c'est le réglage le plus déterminant.")
                    st.write(f"Votre plage cible dépend de la discipline ({ss['discipline']}), de votre objectif ({ss['goal']}) et de votre souplesse ({ctx_flex}).")
            note("⚠️ Les plages cibles sont indicatives et issues des pratiques courantes de bike-fitting. Elles ne remplacent ni un fitting en studio avec capture dynamique, ni l'avis d'un professionnel de santé en cas de douleur persistante.")

    # --- selle & recul
    with t_sel:
        for r in recs:
            if r["key"] in ("knee", "ankle"):
                insight(r)
        st.markdown("##### Recul de selle (KOPS)")
        st.caption("Pour mesurer le recul, photographiez le cycliste avec la manivelle à l'horizontale (3 h, pédale avant) et importez la photo ici. À défaut, l'image principale est utilisée si la jambe est dans la bonne position.")
        kfile = st.file_uploader("Photo manivelle à 3 h (profil)", type=["jpg", "jpeg", "png"], key="kops_file")
        k_img, k_lms, k_scale, k_side = img, A["lms"], scale, A["side"]
        if kfile is not None:
            kdet = core.detect_image(kfile.getvalue())
            if kdet is None:
                st.error("Aucun corps détecté sur la photo à 3 h.")
                k_img = None
            else:
                k_img, k_lms = kdet["image"], kdet["landmarks"]
                k_side = core.auto_side(k_lms) if ss["side_choice"] == "Auto" else ss["side_choice"]
                kp, _ = core.side_points(k_lms, k_side, k_img.shape[1], k_img.shape[0])
                k_scale = core.auto_scale(kp, ctx["height"])
        if k_img is not None:
            kres = core.kops_analysis(k_lms, k_side, k_img.shape[1], k_img.shape[0], k_scale)
            if not kres["crank_ok"]:
                st.warning(f"Le genou est à {kres['knee_angle']:.0f}° : la manivelle ne semble pas à l'horizontale (3 h). Le résultat ci-dessous est donc peu fiable.")
            stretch(st.image, core.annotate_kops(k_img, kres), caption="Ligne jaune : axe de pédale estimé · ligne colorée : genou")
            lvl, title, diag, acts = core.kops_recommendation(kres)
            card(lvl, title, diag, acts, why="Le recul de selle répartit le poids entre selle et cintre et modifie le travail des quadriceps et des fessiers.")
            if kres["crank_ok"]:
                extras.append(("Recul de selle (KOPS)", f"{title} — {diag}"))
            st.caption("L'axe de pédale est estimé à partir de la position du pied (≈ 72 % entre talon et orteil) : mesure indicative.")
        st.markdown("##### Hauteur de selle de référence")
        if ctx["inseam"] > 0:
            e = ctx["inseam"]
            x1, x2, x3 = st.columns(3)
            x1.metric("LeMond (0,883 × entrejambe)", f"{e * 0.883:.1f} cm", help="Axe du boîtier de pédalier → dessus de selle")
            x2.metric("Hamley (1,09 × entrejambe)", f"{e * 1.09:.1f} cm", help="Axe de pédale au point bas → dessus de selle")
            x3.metric("Taille de cadre route (≈ 0,665 × entrejambe)", f"{e * 0.665:.1f} cm", help="Tube de selle, très indicatif.")
            st.caption("Ces formules donnent un point de départ ; la mesure par l'angle du genou est plus fiable pour affiner.")
        else:
            st.info("Renseignez votre entrejambe dans la barre latérale pour afficher les hauteurs de selle de référence (LeMond, Hamley).")
        d_now = core.hip_ankle_dist(m["knee"], seg)
        y1, y2 = st.columns(2)
        y1.metric("Distance hanche → cheville", f"{d_now / 10:.1f} cm", help="Estimée avec votre calibration ou un modèle anthropométrique.")
        y2.metric("Inclinaison de la jambe", f"{leg_tilt:.0f}°", help="Écart de l'axe hanche-cheville par rapport à la verticale (≈ 6 h si < 30°).")

    # --- tronc & cockpit
    with t_tro:
        for r in recs:
            if r["key"] in ("torso", "hip", "shoulder", "elbow"):
                insight(r)
        note("💡 Le cockpit se règle avec la potence (longueur, angle) et la hauteur du cintre. Relever le cintre de 10 mm modifie le tronc d'environ 1 à 2°. Ajustez par pas de 10 mm et testez le simulateur avant de modifier votre vélo.")

    # --- cales & matériel
    with t_mat:
        st.markdown("##### Longueur de manivelle et largeur de cintre")
        z1, z2 = st.columns(2)
        with z1:
            if ctx["inseam"] > 0:
                best, raw = core.crank_length_suggestion(ctx["inseam"])
                st.metric("Manivelle conseillée", f"{best:g} mm", help=f"Environ 21,6 % de l'entrejambe ({raw:.0f} mm), arrondie au format standard.")
                st.caption("Un écart de 2,5 mm n'a pas d'effet mesurable ; au-delà de 5 mm, adaptez aussi la hauteur de selle.")
            else:
                st.info("Renseignez l'entrejambe pour une suggestion de manivelle.")
        with z2:
            if ss["shoulder_w"] > 0:
                st.metric("Largeur de cintre conseillée", f"{core.bar_width_suggestion(ss['shoulder_w'])} cm", help="Proche de la largeur de vos épaules, mesurée entre les points osseux.")
                st.caption("Un cintre plus large ouvre la cage thoracique ; plus étroit, il est plus aérodynamique mais moins stable.")
            else:
                st.info("Renseignez la largeur d'épaules pour une suggestion de cintre.")
        st.markdown("##### Cales et pied")
        ank = next(r for r in recs if r["key"] == "ankle")
        insight(ank)
        card("warn" if ev["ankle"]["dir"] != "in" else "ok", "Réglage des cales — points de contrôle",
             "La photo ne permet pas de mesurer directement les cales. Voici la procédure de contrôle :",
             ["<b>Avant-arrière</b> : l'articulation du gros orteil à l'aplomb de l'axe de pédale. Plus en avant, la charge sur le mollet augmente ; plus en arrière, elle diminue.",
              "<b>Rotation</b> : laissez le pied pivoter naturellement ; une rotation forcée sollicite le genou.",
              "<b>Écartement</b> : réglez pour que les genoux restent alignés avec les hanches (voir l'onglet Vue de face).",
              "Ajustez une seule cale à la fois, par petits pas de 1 à 2 mm.", "Consultez un fitter si vous avez des douleurs de genou ou de pied persistantes."])
        st.markdown("##### Conseils pour votre discipline")
        for tip in core.DISCIPLINE_TIPS[ss["discipline"]]:
            st.markdown(f"- {tip}")
        note("Les cales, la selle (largeur, inclinaison) et le cintre (forme, reach) influencent beaucoup le confort. Les mesurer précisément demande un outil dédié : cette app donne des repères, pas un diagnostic.")

    # --- vue de face
    with t_front:
        st.caption("Importez une photo prise de face ou de dos, le cycliste sur son vélo en position de pédalage, pour évaluer la symétrie et l'alignement des genoux.")
        ff = st.file_uploader("Photo de face ou de dos", type=["jpg", "jpeg", "png"], key="front_file")
        if ff is not None:
            fdet = core.detect_image(ff.getvalue())
            if fdet is None:
                st.error("Aucun corps détecté sur cette photo.")
            else:
                fres = core.analyze_frontal(fdet["image"], fdet["landmarks"])
                fa, fb = st.columns([1, 1], gap="large")
                with fa:
                    stretch(st.image, fres["image"], caption="Bassin, épaules et alignement des jambes")
                with fb:
                    for it in fres["items"]:
                        card(it["status"], it["label"], f"<b>{it['value']:.1f}{it['unit']}</b> — {it['text']}")
                bad = [it for it in fres["items"] if it["status"] != "ok"]
                if bad:
                    extras.append(("Vue de face", " ; ".join(f"{it['label']} : {it['value']:.1f}{it['unit']}" for it in bad)))
                note("En vue de face, les angles dépendent beaucoup de l'objectif et du cadrage : une asymétrie légère (< 2–3°) est normale.")
        else:
            st.info("Aucune photo de face importée.")

    # --- pédalage
    with t_ped:
        vr = A["video"]
        if vr is None:
            st.info("L'analyse dynamique est disponible avec une vidéo : choisissez « 🎬 Vidéo de pédalage » en haut de page. Filmez 10 à 15 secondes de pédalage régulier, de profil, sur home-trainer.")
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Cadence", f"{vr['cadence']:.0f} tr/min")
            k2.metric("Genou au point bas", f"{vr['knee_max']:.1f}°")
            k3.metric("Genou au point haut", f"{vr['knee_min']:.0f}°" if not np.isnan(vr["knee_min"]) else "—")
            k4.metric("Régularité", f"±{vr['bdc_std']:.1f}°")
            fig = go.Figure()
            fig.add_hrect(y0=ranges["knee"][0], y1=ranges["knee"][1], fillcolor="rgba(52,211,153,.12)", line_width=0)
            fig.add_trace(go.Scatter(x=vr["times"], y=vr["knee"], mode="lines", name="Angle du genou", line=dict(color="#22d3ee", width=3)))
            fig.add_trace(go.Scatter(x=[vr["times"][i] for i in vr["bdc"]], y=[vr["knee"][i] for i in vr["bdc"]], mode="markers", name="Point bas",
                                     marker=dict(size=10, color="#fb7185")))
            fig.add_trace(go.Scatter(x=[vr["times"][i] for i in vr["top"]], y=[vr["knee"][i] for i in vr["top"]], mode="markers", name="Point haut",
                                     marker=dict(size=10, color="#a78bfa")))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=330, margin=dict(l=10, r=10, t=10, b=10), font=dict(color="#cbd5e1"),
                              xaxis=dict(title="Temps (s)", gridcolor="rgba(148,163,184,.12)"), yaxis=dict(title="Genou (°)", gridcolor="rgba(148,163,184,.12)"),
                              legend=dict(orientation="h", y=1.12))
            stretch(st.plotly_chart, fig)
            st.caption(f"Zone verte : plage cible du genou ({ranges['knee'][0]}–{ranges['knee'][1]}°). Valeurs moyennées sur {len(vr['bdc'])} tours de manivelle ; image affichée : le tour le plus représentatif.")
            for lvl, title, txt in core.pedal_notes(vr):
                card(lvl, title, txt)
                if lvl != "ok":
                    extras.append((f"Pédalage — {title}", txt))
            note("Une vidéo à 20 images/s et une cadence supérieure à 100 tr/min réduisent la précision. Pour une analyse fiable, évitez de filmer de trois-quarts.")

    # --- mobilité & douleurs
    with t_mob:
        st.markdown("##### Questionnaire de mobilité")
        st.caption("Réalisez ces tests simples. Cochez « Affiner avec le questionnaire de mobilité » dans la barre latérale pour que vos résultats ajustent les plages cibles.")
        for t in core.MOBILITY_TESTS:
            st.radio(t["title"], t["options"], key="mob_" + t["key"], horizontal=True, help=t["help"])
        prof = core.mobility_profile(mobility_answers())
        mc1, mc2 = st.columns(2)
        mc1.metric("Score de mobilité", f"{prof['score']:.0f}/100")
        mc2.metric("Profil de souplesse", prof["flex_label"])
        if not ss["use_mob"]:
            st.info("Ces résultats ne modifient pas encore les plages cibles : activez l'option dans la barre latérale.")
        else:
            st.success(f"Plages cibles ajustées : tronc {prof['shifts']['torso']:+d}°, hanche {prof['shifts']['hip']:+d}°, épaule {prof['shifts']['shoulder']:+d}°.")
        for lvl, title, txt in prof["notes"]:
            card(lvl, title, txt, tag="Exercice conseillé")
        if prof["notes"]:
            extras.append(("Mobilité — exercices", " ; ".join(f"{t} : {x}" for _, t, x in prof["notes"][:3])))
        st.markdown("##### Douleurs et mesures")
        if not ss["complaints"]:
            st.info("Sélectionnez vos douleurs dans la barre latérale pour les rapprocher des mesures de cette analyse.")
        pains = core.pain_analysis(ss["complaints"], ev)
        for lvl, name, txt in pains:
            card(lvl, name, txt, tag="Lien probable" if lvl == "bad" else "Pas de lien direct")
        if pains:
            extras.append(("Douleurs signalées", " ; ".join(f"{n} ({'lien probable' if l == 'bad' else 'pas de lien direct'})" for l, n, _ in pains)))
            note("🩺 Une douleur persistante doit être évaluée par un professionnel de santé. Cet outil propose des pistes de réglage, pas un diagnostic.")

    # --- simulateur
    with t_sim:
        st.markdown("##### Simulez un réglage avant de le faire")
        s1, s2 = st.columns(2, gap="large")
        with s1:
            d_sel = st.slider("Hauteur de selle (mm)", -30, 30, 0, 1, help="Positif = monter la selle")
        with s2:
            d_bar = st.slider("Hauteur de cintre (mm)", -40, 40, 0, 1, help="Positif = relever le cintre")
        new = dict(m)
        new["knee"] = core.knee_after_delta(m["knee"], d_sel, seg)
        new["torso"] = core.torso_after_bar_delta(m["torso"], d_bar, ctx["height"])
        new["hip"] = m["hip"] + (new["torso"] - m["torso"])
        ev_new = core.evaluate_all(new, ranges)
        score_new = core.global_score(ev_new)
        x1, x2, x3 = st.columns(3)
        x1.metric("Score postural", f"{score_new:.0f}/100", f"{score_new - gscore:+.0f}")
        x2.metric("Genou", f"{new['knee']:.1f}°", f"{new['knee'] - m['knee']:+.1f}°")
        x3.metric("Tronc", f"{new['torso']:.1f}°", f"{new['torso'] - m['torso']:+.1f}°")
        z1, z2 = st.columns(2)
        with z1:
            metric_card("knee", new["knee"], ev_new["knee"], ranges["knee"])
        with z2:
            metric_card("torso", new["torso"], ev_new["torso"], ranges["torso"])
        sc_new = {k: ev_new[k]["score"] for k in ORDER}
        stretch(st.plotly_chart, radar(sc_new, "Après réglage", scores))
        note("Modèle simplifié : la selle se déplace verticalement et l'épaule suit le cintre. Le recul de selle, la longueur de potence et les cales ne sont pas simulés. Validez toujours par une nouvelle analyse.")

    # --- transfert de réglages
    with t_tr:
        st.markdown("##### Transférer vos réglages d'un vélo à un autre")
        st.caption("Mesurez votre vélo de référence (celui sur lequel vous êtes bien) et le nouveau vélo, puis obtenez la liste des ajustements à faire.")
        ref, cur = {}, {}
        ca, cb = st.columns(2, gap="large")
        ca.markdown("**Vélo de référence**")
        cb.markdown("**Nouveau vélo**")
        for key, label, helptxt, default in core.TRANSFER_FIELDS:
            va = ca.number_input(label, value=float(default), step=1.0, key=f"tr_ref_{key}", help=helptxt or None)
            vb = cb.number_input(label, value=float(default), step=1.0, key=f"tr_cur_{key}", help=helptxt or None)
            ref[key], cur[key] = va, vb
        plan = core.transfer_plan(ref, cur)
        st.markdown("##### Ajustements à effectuer")
        for p in plan:
            card(p["status"], p["label"], f"Référence : <b>{p['ref']:g}</b> · Nouveau vélo : <b>{p['cur']:g}</b>", [p["action"]], tag="À régler" if p["status"] != "ok" else "OK")
        note("L'ordre conseillé : manivelle, hauteur de selle, recul, puis allonge et dénivelé du cockpit. Terminez par une nouvelle analyse posturale pour valider.")

    # --- suivi
    with t_follow:
        st.markdown(f"##### Enregistrer cette analyse — {active}")
        cur_dict = dict(m=m, score=gscore, annotated=annotated, source=A["source"], quality=quality, ev=ev,
                        extra=dict(cadence=round(A["video"]["cadence"], 1), rom=round(A["video"]["rom"], 1)) if A["video"] and not np.isnan(A["video"]["rom"]) else {})
        history_section(active, cur_dict, kp="an_")

    # --- rapport
    with t_rep:
        st.markdown("##### Rapport personnalisé")
        r1, r2 = st.columns(2)
        studio_name = r1.text_input("Nom du studio / de la marque", value=ss["studio"] if fitter else "", key="rep_studio", placeholder="VeloFit AI Studio")
        client_name = r2.text_input("Nom du cycliste", value=active if active != "Invité" else "", key="rep_client")
        logo_file = st.file_uploader("Logo (optionnel)", type=["png", "jpg", "jpeg"], key="rep_logo")
        logo_bytes = logo_file.getvalue() if logo_file is not None else (ss["logo_png"] if fitter else None)
        rep = core.assemble_report(ctx, m, ev, ranges, gscore, recs, quality, annotated, studio=studio_name, client=client_name, logo_bytes=logo_bytes, extras=extras)
        b1, b2, b3 = st.columns(3)
        if b1.button("📄 Générer le PDF", key="mk_pdf"):
            with st.spinner("Création du PDF…"):
                ss["_pdf"] = core.report_pdf(rep)
        if ss.get("_pdf"):
            b1.download_button("⬇️ Télécharger le PDF", ss["_pdf"], "velofit_rapport.pdf", "application/pdf", key="dl_pdf")
        b2.download_button("🌐 Rapport HTML (imprimable)", core.report_html(rep).encode("utf-8"), "velofit_rapport.html", "text/html", key="dl_html")
        b3.download_button("📝 Rapport Markdown", core.report_markdown(rep).encode("utf-8"), "velofit_rapport.md", "text/markdown", key="dl_md")
        df_m = pd.DataFrame([{"Mesure": META[k]["label"], "Valeur (°)": round(m[k], 1), "Cible min": ranges[k][0], "Cible max": ranges[k][1],
                              "Statut": STATUS[ev[k]["status"]][1], "Score": round(scores[k])} for k in ORDER])
        e1, e2 = st.columns(2)
        e1.download_button("🖼️ Image annotée (PNG)", core.png_bytes(annotated), "velofit_analyse.png", "image/png", key="dl_png")
        e2.download_button("📊 Mesures (CSV)", df_m.to_csv(index=False).encode("utf-8"), "velofit_mesures.csv", "text/csv", key="dl_csv")
        note("Le PDF reprend le score, l'image annotée, les mesures, le plan d'action et les sections complétées dans les autres onglets (recul de selle, vue de face, pédalage, douleurs, mobilité).")
