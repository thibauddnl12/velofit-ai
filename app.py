# ==============================================================================
#  VeloFit AI Studio v4 — Laboratoire d'analyse posturale pour le vélo
#  Lancement :  streamlit run app.py
#  Fichiers à placer dans le même dossier : velofit_core.py, accounts.py, auth_ui.py,
#  mailer.py, ui_kit.py et bike3d.py
# ==============================================================================
import hashlib
import html as _html
import os
import re
import tempfile
from functools import partial
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import streamlit.components.v1 as components
except Exception:  # futures versions sans ce module : st.iframe prend le relais
    components = None

import accounts as acc
import auth_ui
import bike3d
import ui_kit
import velofit_core as core
from velofit_core import META, ORDER, STATUS

st.set_page_config(page_title="VeloFit AI — Studio Postural", page_icon="🚴", layout="wide", initial_sidebar_state="auto")

# ------------------------------------------------------------------------------
#  DESIGN
# ------------------------------------------------------------------------------
st.markdown(ui_kit.CSS, unsafe_allow_html=True)


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


def section(title, sub="", first=False):
    """Titre de section avec une phrase d'explication : le même repère visuel partout."""
    H(ui_kit.section(title, sub, first))


def embed_html(page: str, height: int) -> bool:
    """Affiche une page HTML autonome (le vélo 3D). Retourne False si la version de Streamlit ne le permet pas.

    st.iframe remplace st.components.v1.html, déprécié depuis Streamlit 1.56 : on essaie le premier, puis le second."""
    if hasattr(st, "iframe"):
        try:
            st.iframe(page, height=height)
            return True
        except Exception:
            pass
    if components is not None and hasattr(components, "html"):
        try:
            components.html(page, height=height, scrolling=False)
            return True
        except Exception:
            pass
    return False


# ------------------------------------------------------------------------------
#  CONNEXION OBLIGATOIRE ET STOCKAGE ISOLÉ PAR COMPTE
# ------------------------------------------------------------------------------
user = auth_ui.gate()            # affiche la page de connexion et arrête le script si besoin
SC = user["username"]
IS_ADMIN = user["role"] == "admin"
_STORE_FNS = ("list_profiles", "load_profile", "save_profile", "load_history", "add_history", "update_history_entry",
              "delete_history_entry", "load_history_image", "profile_summary")
store = SimpleNamespace(**{n: partial(getattr(core, n), scope=SC) for n in _STORE_FNS})
ss = st.session_state


# ------------------------------------------------------------------------------
#  ÉTAT ET PROFIL
# ------------------------------------------------------------------------------
SHOT_MODES = ["À l'arrêt, en posant (pédale en bas)", "En pédalant (photo prise en roulant)"]
DEFAULTS = dict(height=175, weight=0, inseam=0, shoulder_w=0, flex="Moyenne", discipline="Route / Endurance", goal="Équilibré",
                side_choice="Auto", complaints=[], target_score=85, use_mob=False, learn=True, show_grid=False, shot_mode=SHOT_MODES[0],
                mode="Cycliste", profile_name="", studio="", logo_png=None)
FLEX_OPTS = ["Limitée", "Moyenne", "Très souple"]
GOAL_OPTS = ["Confort", "Équilibré", "Performance"]
MOB_KEYS = ["mob_" + t["key"] for t in core.MOBILITY_TESTS]
PROFILE_KEYS = ["height", "weight", "inseam", "shoulder_w", "flex", "discipline", "goal", "target_score", "use_mob", "complaints"] + MOB_KEYS
LIMITS = dict(height=(140, 215), weight=(0, 200), inseam=(0, 110), shoulder_w=(0, 60), target_score=(50, 100))
NEW_LABEL = "+ Nouveau profil"


def _mob_default(t):
    return t["options"][len(t["options"]) // 2]


for _k, _v in DEFAULTS.items():
    ss.setdefault(_k, list(_v) if isinstance(_v, list) else _v)
for _t in core.MOBILITY_TESTS:
    ss.setdefault("mob_" + _t["key"], _mob_default(_t))
# Les réglages restent mémorisés même quand leur champ n'est pas affiché (ex. pendant la création du profil).
for _k in PROFILE_KEYS + ["profile_name", "mode", "learn", "side_choice", "show_grid", "shot_mode"]:
    ss[_k] = ss[_k]


def reset_profile_fields():
    for k in PROFILE_KEYS:
        if k in DEFAULTS:
            ss[k] = list(DEFAULTS[k]) if isinstance(DEFAULTS[k], list) else DEFAULTS[k]
    for t in core.MOBILITY_TESTS:
        ss["mob_" + t["key"]] = _mob_default(t)
    ss["profile_name"] = ""


def apply_profile(name):
    """Charge un profil enregistré dans l'état courant, en corrigeant les valeurs absentes ou hors limites."""
    p = store.load_profile(name)
    ss["profile_name"] = name
    for k in PROFILE_KEYS:
        if k in p:
            ss[k] = p[k]
    if "weight" not in p:
        ss["weight"] = 0                      # profil créé avant l'ajout du poids : à compléter
    for k, (lo, hi) in LIMITS.items():
        try:
            ss[k] = max(lo, min(hi, int(round(float(ss[k])))))
        except (TypeError, ValueError):
            ss[k] = DEFAULTS[k]
    ss["target_score"] = int(round(ss["target_score"] / 5) * 5)
    ss["discipline"] = core.norm_discipline(ss["discipline"])        # reprend aussi l'ancien nom « Triathlon / CLM »
    if ss["flex"] not in FLEX_OPTS:
        ss["flex"] = DEFAULTS["flex"]
    if ss["goal"] not in GOAL_OPTS:
        ss["goal"] = DEFAULTS["goal"]
    ss["use_mob"] = bool(ss["use_mob"])
    ss["complaints"] = [c for c in (ss["complaints"] or []) if c in core.COMPLAINTS]
    for t in core.MOBILITY_TESTS:
        if ss["mob_" + t["key"]] not in t["options"]:
            ss["mob_" + t["key"]] = _mob_default(t)


def _load_profile_cb():
    sel = ss.get("profile_sel", NEW_LABEL)
    if sel == NEW_LABEL:
        reset_profile_fields()
    else:
        apply_profile(sel)


def mobility_answers():
    ans = {}
    for t in core.MOBILITY_TESTS:
        v = ss.get("mob_" + t["key"], _mob_default(t))
        ans[t["key"]] = t["options"].index(v) if v in t["options"] else len(t["options"]) // 2
    return ans


def save_profile_now(require_weight=False):
    """Enregistre le profil affiché. Retourne (ok, nom ou message d'erreur)."""
    name = (ss["profile_name"] or "").strip()
    if not name:
        return False, "Donnez un nom au profil avant de l'enregistrer."
    if require_weight and int(ss["weight"]) < 30:
        return False, "Indiquez votre poids (en kg) : il sert au calcul de la pression des pneus et des watts par kilo."
    store.save_profile(name, {k: ss[k] for k in PROFILE_KEYS})   # (le champ « nom » existe déjà à l'écran : on ne le réécrit pas ici)
    return True, name


# --- au début de la session : le dernier profil enregistré est rechargé automatiquement
if ss.get("_pending_sel") is not None:
    ss["profile_sel"] = ss.pop("_pending_sel")
profiles = store.list_profiles()
if ss.get("_boot") != SC:
    ss["_boot"] = SC
    reset_profile_fields()
    if profiles:
        apply_profile(profiles[0])
        ss["profile_sel"] = profiles[0]
if ss.get("profile_sel") not in [NEW_LABEL] + profiles:
    ss["profile_sel"] = ss["profile_name"] if ss["profile_name"] in profiles else NEW_LABEL

fitter = ss["mode"].startswith("Fitter")
who = "client" if fitter else "profil"


def profile_fields(first=False):
    """Champs du profil, dans l'ordre où ils comptent pour les calculs. À appeler dans un st.form."""
    H(ui_kit.form_section("1 · Vélo et pratique", "Le type de vélo fixe les angles visés : on ne règle pas un vélo de triathlon comme un VTT.", first=True))
    c1, c2 = st.columns(2)
    c1.selectbox("Type de vélo / discipline", list(core.BASE_RANGES.keys()), key="discipline")
    c2.select_slider("Objectif", GOAL_OPTS, key="goal", help="Confort : position plus relevée. Performance : position plus basse et plus aérodynamique.")
    H(ui_kit.form_section("2 · Morphologie", "La taille et l'entrejambe servent à convertir les angles en millimètres ; le poids, à la pression des pneus et aux watts par kilo."))
    a, b = st.columns(2)
    a.number_input("Taille (cm)", 140, 215, step=1, key="height")
    b.number_input("Poids (kg)", 0, 200, step=1, key="weight", help="À saisir : 0 = non renseigné. Sert à la pression des pneus et aux watts par kilo.")
    a.number_input("Entrejambe (cm) — optionnel", 0, 110, step=1, key="inseam", help="0 = non renseigné. Sert aux formules de hauteur de selle et à la longueur de manivelle.")
    b.number_input("Largeur d'épaules (cm) — optionnel", 0, 60, step=1, key="shoulder_w", help="Distance entre les deux points osseux des épaules. Sert à la largeur de cintre.")
    st.select_slider("Souplesse (ischios / dos)", FLEX_OPTS, key="flex", help="Une souplesse limitée demande une position plus relevée.")
    st.checkbox("Affiner la souplesse avec le questionnaire de mobilité", key="use_mob",
                help="Les tests se trouvent dans Analyses complémentaires › Mobilité & douleurs. Les plages cibles s'adaptent alors à vos résultats.")
    H(ui_kit.form_section("3 · Douleurs et objectif de score", "Vos douleurs sont rapprochées des mesures pour repérer le réglage en cause."))
    st.multiselect("Douleurs ressenties à vélo (laisser vide s'il n'y en a pas)", list(core.COMPLAINTS.keys()), key="complaints")
    st.slider("Score postural visé", 50, 100, step=5, key="target_score", help="Sert de repère dans le suivi de vos analyses.")
    H(ui_kit.form_section("4 · Nom du profil", "Il apparaît dans l'historique et sur les rapports."))
    st.text_input(f"Nom du {who}", key="profile_name", placeholder="ex. Thibaud — vélo de route")


def profile_text():
    """Résumé court du profil pour l'en-tête et le bandeau d'étapes."""
    bits = [ss["discipline"], f"{int(ss['height'])} cm"]
    if int(ss["weight"]) > 0:
        bits.append(f"{int(ss['weight'])} kg")
    return " · ".join(bits)


# ------------------------------------------------------------------------------
#  CRÉATION DU PROFIL (premier accès) : ces données passent avant tout le reste
# ------------------------------------------------------------------------------
if not profiles and ss.get("_onboarded") != SC:
    with st.sidebar:
        st.markdown("### VeloFit AI")
        auth_ui.sidebar_box(user)
    if not ss["profile_name"]:
        ss["profile_name"] = SC
    H(ui_kit.appbar("VeloFit AI Studio", "Bienvenue ! Commençons par votre profil."))
    H(ui_kit.stepper([("Votre profil", "Vélo, morphologie, douleurs", "now"),
                      ("Photo ou vidéo", "De profil, sur home-trainer", "todo"),
                      ("Résultats", "Score, réglages, vélo 3D", "todo")]))
    section("Créez votre profil", "Ces informations règlent les angles visés et convertissent les mesures en millimètres : sans elles, les conseils seraient "
                                  "génériques. Une minute suffit, et tout reste modifiable ensuite dans l'onglet « Mon profil ».", first=True)
    with st.form("onboarding_form"):
        profile_fields(first=True)
        go_first = st.form_submit_button("Enregistrer et commencer", type="primary")
        skip = st.form_submit_button("Plus tard (administration seulement)") if IS_ADMIN else False
    if go_first:
        ok, res = save_profile_now(require_weight=True)
        if ok:
            ss["_onboarded"] = SC
            ss["_pending_sel"] = res
            st.rerun()
        else:
            st.error(res)
    elif skip:
        ss["_onboarded"] = SC
        st.rerun()
    st.stop()


# ------------------------------------------------------------------------------
#  BARRE LATÉRALE : compte, profil actif, affichage
# ------------------------------------------------------------------------------
active = (ss["profile_name"] or "").strip() or "Invité"
with st.sidebar:
    st.markdown("### VeloFit AI")
    auth_ui.sidebar_box(user)
    st.markdown(f'<div class="side-sec">{"Client actif" if fitter else "Profil actif"}</div>', unsafe_allow_html=True)
    _w = int(ss["weight"])
    H(ui_kit.profile_card(active, [
        ("Vélo", ss["discipline"], False),
        ("Taille", f"{int(ss['height'])} cm", False),
        ("Poids", f"{_w} kg" if _w > 0 else "à compléter", _w <= 0),
        ("Objectif", ss["goal"], False),
        ("Souplesse", ss["flex"], False),
    ]))
    st.caption(f"Pour le modifier ou en changer : onglet « {'Fiche client' if fitter else 'Mon profil'} ».")
    st.markdown('<div class="side-sec">Affichage</div>', unsafe_allow_html=True)
    st.radio("Mode d'utilisation", ["Cycliste", "Fitter (professionnel)"], key="mode", horizontal=False,
             help="Le mode Fitter gère plusieurs clients, personnalise les rapports (logo, nom du studio) et affiche un tableau de bord.")
    st.checkbox("Explications pédagogiques", key="learn", help="Affiche pourquoi chaque angle compte (idéal pour débuter).")
    with st.expander("Protocole rapide"):
        st.markdown("- Profil strict, côté de la jambe mesurée\n- Vélo sur home-trainer\n- Photo : manivelle au **point mort bas** (6 h)\n- Vidéo : 10 à 15 s de pédalage régulier\n- Appareil à hauteur de hanche, ~3 m")

ctx_flex = ss["flex"]
extra_shift = {}
mob = None
if ss["use_mob"]:
    mob = core.mobility_profile(mobility_answers())
    ctx_flex = mob["flex_label"]
    extra_shift = mob["shifts"]
ranges = core.get_ranges(ss["discipline"], ctx_flex, ss["goal"], extra_shift)
ctx = dict(height=int(ss["height"]), weight=int(ss["weight"]), inseam=int(ss["inseam"]), shoulder_w=int(ss["shoulder_w"]),
           flex=ctx_flex, discipline=ss["discipline"], goal=ss["goal"])

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
      <div class="mcard-top"><span class="mcard-label">{meta['label']}</span><span class="chip" style="--c:{color}">{label}</span></div>
      <div class="mcard-value">{value:.1f}<small>°</small></div>
      <div class="gauge"><div class="gauge-zone" style="left:{z0}%;width:{z1 - z0}%"></div><div class="gauge-mark" style="left:{pos}%"></div></div>
      <div class="gauge-scale"><span>{meta['vmin']}°</span><span>cible {rng[0]}–{rng[1]}°</span><span>{meta['vmax']}°</span></div>
    </div>""")


def card(status, title, body, actions=None, tag=None, why=None):
    color, label = STATUS[status]
    ul = "<ul>" + "".join(f"<li>{a}</li>" for a in actions) + "</ul>" if actions else ""
    wy = f'<p class="why">{why}</p>' if why and ss["learn"] else ""
    H(f'<div class="insight" style="--c:{color}"><div class="insight-h"><span class="chip" style="--c:{color}">{tag or label}</span><b>{title}</b></div>'
      f"<p>{body}</p>{wy}{ul}</div>")


def insight(rec):
    card(rec["status"], rec["title"], rec["diag"], rec["actions"], why=rec.get("why"))


def score_ring(score, partial=False):
    color = ui_kit.OK if score >= 80 else (ui_kit.WARN if score >= 60 else ui_kit.BAD)
    title, sub = core.verdict_for(score)
    if partial:
        color = ui_kit.MUT
        title, sub = "Score partiel", ("Calculé sur le haut du corps seulement (tronc, épaule, coude). Le genou, la hanche et la cheville "
                                       "ne sont pas jugés : reprenez une photo manivelle à 6 h pour un score complet.")
    H(f"""
    <div class="glass"><div class="score-wrap">
      <div class="ring" style="--p:{score:.0f};--c:{color}"><div class="ring-in"><div><div class="ring-val">{score:.0f}</div><div class="ring-sub">{"partiel" if partial else "/ 100"}</div></div></div></div>
      <div class="verdict"><h3>{title}</h3><p>{sub}</p></div>
    </div></div>""")


def radar(scores, title_b="Votre position", scores_b=None):
    labels = [META[k]["short"] for k in ORDER]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[100] * (len(ORDER) + 1), theta=labels + [labels[0]], mode="lines",
                                  line=dict(color="rgba(52,211,153,.45)", dash="dot"), hoverinfo="skip", name="Idéal"))
    if scores_b is not None:
        vb = [scores_b[k] for k in ORDER]
        fig.add_trace(go.Scatterpolar(r=vb + [vb[0]], theta=labels + [labels[0]], fill="toself", name=title_b,
                                      line=dict(color="#5ec8ff", width=2), fillcolor="rgba(94,200,255,.14)"))
    vals = [scores[k] for k in ORDER]
    fig.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill="toself", name="Actuel" if scores_b is not None else title_b,
                                  line=dict(color="#c6f432", width=3), fillcolor="rgba(198,244,50,.18)"))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,.10)", tickfont=dict(color="#8b97a8", size=9)),
                                 angularaxis=dict(gridcolor="rgba(255,255,255,.10)", tickfont=dict(color="#c9d2de", size=11))),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=scores_b is not None, legend=dict(font=dict(color="#c9d2de")),
                      margin=dict(l=40, r=40, t=20, b=20), height=340, font=dict(family="Inter"))
    return fig


def line_fig(x, series, height=300, target=None, ytitle=""):
    fig = go.Figure()
    for name, y, color in series:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(color=color, width=3), marker=dict(size=8)))
    if target is not None:
        fig.add_hline(y=target, line_dash="dot", line_color="#34d399", annotation_text="objectif", annotation_font_color="#34d399")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height, margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(family="Inter", color="#c9d2de"), xaxis=dict(gridcolor="rgba(255,255,255,.07)"),
                      yaxis=dict(gridcolor="rgba(255,255,255,.07)", title=ytitle), legend=dict(orientation="h", y=1.12))
    return fig


def landing():
    """Avant toute analyse : d'abord quoi faire maintenant, ensuite ce que l'on obtient."""
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        H("""
        <div class="glass"><h4 style="margin:0 0 6px;">Comment prendre la photo ou la vidéo</h4>
          <div class="step"><div class="n">1</div><div><b>Vélo stabilisé</b><br><span>Montez-le sur un home-trainer, position de pédalage naturelle.</span></div></div>
          <div class="step"><div class="n">2</div><div><b>Profil strict</b><br><span>Appareil à hauteur de hanche, à 3 m, perpendiculaire au vélo.</span></div></div>
          <div class="step"><div class="n">3</div><div><b>Photo ou vidéo</b><br><span>Photo à 6 h (point mort bas) ou 10 à 15 s de pédalage régulier.</span></div></div>
          <div class="step"><div class="n">4</div><div><b>Tenue ajustée</b><br><span>Vêtements près du corps et contrastés, bon éclairage, corps entier cadré.</span></div></div>
        </div>""")
    with right:
        H("""
        <div class="glass"><h4 style="margin:0 0 10px;">Ce que nous mesurons</h4>
          <p style="color:#9aa6b8;font-size:.94rem;line-height:1.6;margin:0 0 12px;">Six angles biomécaniques sont comparés à des plages cibles adaptées à votre discipline, votre souplesse et votre objectif.</p>
          <span class="chip" style="--c:#c6f432">Genou</span> <span class="chip" style="--c:#5ec8ff">Tronc</span> <span class="chip" style="--c:#c6f432">Hanche</span>
          <span class="chip" style="--c:#5ec8ff">Épaule</span> <span class="chip" style="--c:#c6f432">Coude</span> <span class="chip" style="--c:#5ec8ff">Cheville</span>
        </div>""")
    section("Ce que vous obtiendrez", "Une fois la photo ou la vidéo importée, l'analyse s'affiche en quelques secondes.")
    feats = [
        ("video", "Photo, vidéo ou caméra", "Analyse statique au point mort bas ou dynamique sur 10 s de pédalage : cadence, régularité, amplitude du genou."),
        ("target", "Score postural /100", "Six angles pondérés, un radar et un plan d'action priorisé et chiffré en millimètres."),
        ("ruler", "Vélo 3D et calibration", "Les réglages à faire sont montrés sur un vélo en 3D que vous faites tourner, avec les valeurs en vrais millimètres."),
        ("compass", "Recul de selle & vue de face", "Position du genou par rapport à l'axe de pédale (KOPS), symétrie du bassin et alignement des genoux."),
        ("activity", "Mobilité & douleurs", "Questionnaire de souplesse qui adapte les cibles, et mise en relation de vos douleurs avec les mesures."),
        ("history", "Suivi & transfert", "Historique par profil, comparaison avant/après, objectif de score et transfert des réglages d'un vélo à un autre."),
    ]
    for row in (feats[:3], feats[3:]):
        cols = st.columns(3, gap="medium")
        for c, (ico, t, d) in zip(cols, row):
            with c:
                H(f'<div class="glass feat"><div class="ico">{ui_kit.ICONS[ico]}</div><h4>{t}</h4><p>{d}</p></div>')


def targets_table(rng, discipline, dynamic=False):
    """Tableau « angle, cible, niveau de preuve, source » pour la discipline, puis liste des références et limites de la mesure."""
    basis = core.range_basis(discipline)
    used, rows = [], []
    for k in ORDER:
        level, text, refs = basis[k]
        for r_ in refs:
            if r_ not in used:
                used.append(r_)
        marks = " ".join(f"[{used.index(r_) + 1}]" for r_ in refs)
        col = ui_kit.OK if level == "étude" else ui_kit.ACCENT_2
        rows.append(f'<div class="adj tgt" style="--c:{col}"><div class="t"><b>{_html.escape(META[k]["short"])} : {rng[k][0]}–{rng[k][1]}° '
                    f'<span class="chip" style="--c:{col};margin-left:6px">{"Étude publiée" if level == "étude" else "Repère de pratique"}</span></b>'
                    f'<span>{_html.escape(text)} {marks}</span></div></div>')
    H("".join(rows))
    st.caption(f"Cibles pour « {discipline} », {'image prise en pédalant' if dynamic else 'photo posée'}, après prise en compte de votre objectif et de votre souplesse "
               "(qui décalent le tronc et la hanche de quelques degrés).")
    with st.expander("Références et limites de la mesure"):
        for i_, r_ in enumerate(used, 1):
            ref = core.REFERENCES[r_]
            st.markdown(f"[{i_}] {ref['cite']} [Lien]({ref['url']})")
        v = core.REFERENCES["bini2023"]
        st.markdown("**Précision de la mesure par analyse d'image.** Une étude a comparé un réseau de neurones du même type que celui utilisé ici à un système à marqueurs, "
                    "chez 26 cyclistes filmés de profil : l'écart moyen est d'environ 1° pour la hanche et le genou, mais il peut atteindre 6 à 7° sur une mesure isolée ; "
                    "l'accord est faible pour la cheville. Retenez une marge d'environ ± 5° sur chaque angle : un écart de 2 ou 3° par rapport à la cible n'est pas significatif. "
                    f"{v['cite']} [Lien]({v['url']})")
        st.markdown("**Photo posée ou en mouvement.** À 6 h, un genou mesuré en pédalant est plus fléchi d'environ 8° que sur une pose à l'arrêt (Bini & Hume, 2016) : "
                    "les cibles sont donc décalées de 5° quand l'image est prise en pédalant (25–35° de flexion à l'arrêt, 30–40° en pédalant).")
        st.markdown("**Ce que l'application ne mesure pas.** Elle ne voit ni l'alignement du genou de face en mouvement, ni les asymétries du bassin, ni les pressions sur la selle : "
                    "une étude posturale en cabinet reste la référence en cas de douleur persistante.")


def glossary():
    for term, text in core.GLOSSARY_TERMS:
        with st.expander(term):
            st.write(text)


def bike_view(adjustments):
    """Vélo 3D à gauche, liste numérotée des réglages à droite (mêmes numéros)."""
    todo = [a for a in adjustments if a["status"] in ("bad", "warn")]
    info = [a for a in adjustments if a["status"] not in ("bad", "warn")]
    left, right = st.columns([1.25, 0.75], gap="large")
    with left:
        shown = embed_html(bike3d.viewer_html(adjustments, ss["discipline"]), bike3d.HEIGHT)
        if not shown:
            st.info("L'aperçu 3D n'est pas disponible avec cette version de Streamlit : la liste des réglages ci-contre reste complète.")
        else:
            st.caption("Faites glisser pour tourner le vélo. La pièce à déplacer s'anime dans le sens du réglage ; touchez un numéro pour le détail.")
    with right:
        if todo:
            H('<div class="adj-h">Réglages à faire, dans cet ordre</div>' + "".join(ui_kit.adjust_item(a) for a in todo))
            st.caption("Corrigez un paramètre à la fois, dans cet ordre, puis refaites une analyse pour valider.")
        else:
            card("ok", "Aucun réglage prioritaire", "Tous les angles sont dans les plages cibles. Conservez votre configuration et refaites un contrôle après tout changement de matériel.")
        if info:
            H('<div class="adj-h">Repères matériel calculés depuis votre profil</div>' + "".join(ui_kit.adjust_item(a) for a in info))
        elif int(ss["weight"]) <= 0 or int(ss["inseam"]) <= 0:
            st.caption("Renseignez le poids, l'entrejambe et la largeur d'épaules dans « Mon profil » pour obtenir aussi la pression des pneus, la longueur de manivelle et la largeur de cintre.")


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
        if c2.button("Enregistrer", key=f"{kp}save_hist"):
            entry = dict(label=label, note=note_txt, score=round(current["score"], 1), source=current["source"], discipline=ss["discipline"],
                         goal=ss["goal"], quality=round(current["quality"], 1), m={k: round(v, 2) for k, v in current["m"].items()},
                         ev={k: current["ev"][k]["status"] for k in ORDER}, **current.get("extra", {}))
            store.add_history(name, entry, core.png_bytes(current["annotated"]))
            if not (name == "Invité" and name not in store.list_profiles()):
                store.save_profile(name, {k: st.session_state[k] for k in PROFILE_KEYS})
            st.success("Analyse enregistrée dans l'historique.")
            hist = store.load_history(name)
    if not hist:
        st.info("Aucune analyse enregistrée pour ce profil. Après une analyse, ouvrez la rubrique « Enregistrer & comparer » des résultats et cliquez sur « Enregistrer » : "
                "vous pourrez ensuite comparer l'avant / après de vos réglages.")
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
        stretch(st.plotly_chart, line_fig(dates, [("Score", scores, "#c6f432")], target=tgt, ytitle="Score /100"))
    rows = []
    for e in hist:
        r = {"Analyse": e.get("label", "") + (" (score partiel)" if e.get("partial") else ""), "Date": e["date"][:16].replace("T", " "), "Source": e.get("source", ""), "Score": e["score"], "Réglage": e.get("note", "")}
        for k in ORDER:
            r[META[k]["short"]] = e["m"].get(k)
        if e.get("avg_power"):
            r["Puissance moy. (W)"] = round(e["avg_power"])
            if int(ss["weight"]) > 0:
                r["W/kg"] = round(e["avg_power"] / ss["weight"], 2)
        rows.append(r)
    stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)

    if len(hist) >= 2:
        section("Comparer deux analyses", "Choisissez l'analyse « avant » et l'analyse « après » un réglage.")
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

    section("Données de sortie (puissance, fréquence cardiaque)", "Importez l'export CSV d'une sortie pour l'associer à une analyse et suivre le lien entre position et performance.")
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
                if stats["avg_power"]:
                    wkg = (f" — soit **{core.fr_num(round(stats['avg_power'] / ss['weight'], 2))} W/kg** pour {int(ss['weight'])} kg"
                           if int(ss["weight"]) > 0 else " — renseignez votre poids dans le profil pour obtenir les watts par kilo")
                    st.write(f"Puissance moyenne : **{stats['avg_power']:.0f} W**{wkg}")
                else:
                    st.write("Puissance : non trouvée.")
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
                                   marker=dict(size=12, color="#c6f432")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280, margin=dict(l=10, r=10, t=10, b=10), font=dict(color="#c9d2de"),
                          xaxis=dict(title="Score postural", gridcolor="rgba(255,255,255,.07)"), yaxis=dict(title="Puissance moyenne (W)", gridcolor="rgba(255,255,255,.07)"))
        stretch(st.plotly_chart, fig)
        note("Ce graphique montre la relation entre votre score postural et la puissance moyenne de sorties associées. Il est indicatif : la forme du jour, le parcours et la fatigue jouent aussi.")
    with st.expander("Supprimer une analyse"):
        opts_del = {f"{e.get('label', '')} · {e['date'][:16].replace('T', ' ')}": e["id"] for e in hist}
        pick = st.selectbox("Analyse à supprimer", list(opts_del.keys()), key=f"{kp}del_pick")
        if st.button("Supprimer définitivement", key=f"{kp}del_btn"):
            store.delete_history_entry(name, opts_del[pick])
            st.rerun()


# ------------------------------------------------------------------------------
#  EN-TÊTE ET NAVIGATION
# ------------------------------------------------------------------------------
brand = (ss["studio"] or "VeloFit AI Studio") if fitter else "VeloFit AI Studio"
H(ui_kit.appbar(brand, "Analyse posturale à vélo : une photo ou une vidéo de profil, des réglages chiffrés.",
                who=f"{'Client' if fitter else 'Profil'} : <b>{_html.escape(active)}</b><br>{_html.escape(profile_text())}"))

PROFILE_TAB = "Fiche client" if fitter else "Mon profil"
_top_names = ["Analyse", PROFILE_TAB, "Suivi", "Guide"] + (["Clients"] if fitter else []) + (["Administration"] if IS_ADMIN else [])
tabs_top = st.tabs(_top_names)
t_main, t_prof, t_hist_top, t_guide = tabs_top[:4]
t_clients = tabs_top[4] if fitter else None
t_admin = tabs_top[-1] if IS_ADMIN else None

# --- profil : toujours modifiable
with t_prof:
    section(PROFILE_TAB, "Ces données règlent les angles visés et les calculs en millimètres. Modifiez-les puis enregistrez : l'analyse en cours est recalculée aussitôt.", first=True)
    if ss.get("_flash"):
        st.success(ss.pop("_flash"))
    p1, p2 = st.columns([1.2, 1])
    p1.selectbox(f"Ouvrir un {who} existant ou en créer un nouveau", [NEW_LABEL] + profiles, key="profile_sel", on_change=_load_profile_cb)
    if int(ss["weight"]) <= 0:
        st.warning("Le poids n'est pas renseigné : la pression des pneus et les watts par kilo ne peuvent pas être calculés.")
    with st.form("profile_form"):
        profile_fields()
        go_save = st.form_submit_button(f"Enregistrer le {who}", type="primary")
    if go_save:
        ok, res = save_profile_now()
        if ok:
            ss["_flash"] = f"Profil « {res} » enregistré."
            ss["_pending_sel"] = res
            st.rerun()
        else:
            st.error(res)

# --- suivi
with t_hist_top:
    section(f"Suivi de {active}", "Toutes vos analyses enregistrées, l'évolution du score et la comparaison avant / après.", first=True)
    history_section(active, kp="top_")

# --- guide
with t_guide:
    section("Comment prendre une bonne photo ou vidéo", "La qualité de la prise de vue fait la fiabilité des mesures.", first=True)
    st.markdown("- Vélo sur home-trainer, position de pédalage naturelle\n- Appareil à hauteur de hanche, à environ 3 m, perpendiculaire au vélo (profil strict)\n"
                "- Photo : manivelle au **point mort bas** (6 h), côté de la jambe mesurée vers l'appareil\n- Vidéo : 10 à 15 s de pédalage régulier\n"
                "- Vêtements ajustés et contrastés, bon éclairage, corps entier dans le cadre")
    section(f"Conseils pour la discipline « {ss['discipline']} »")
    for tip in core.DISCIPLINE_TIPS[ss["discipline"]]:
        st.markdown(f"- {tip}")
    section("D'où viennent les angles visés", "Chaque cible est rattachée à une étude publiée quand il en existe une, sinon à un repère de bike-fitters, signalé comme tel.")
    targets_table(core.get_ranges(ss["discipline"], ctx_flex, ss["goal"], extra_shift), ss["discipline"])
    section("Glossaire", "Les mots du bike-fitting utilisés dans l'application.")
    glossary()

# --- clients (mode fitter)
if fitter:
    with t_clients:
        section("Vos clients", "Tableau de bord de tous les profils enregistrés sur ce compte.", first=True)
        if not profiles:
            st.info("Aucun client enregistré. Créez-en un dans l'onglet « Fiche client ».")
        else:
            rows = []
            for p in profiles:
                s = store.profile_summary(p)
                rows.append({"Client": p, "Analyses": s["n"], "Dernier score": s["last_score"], "Dernière visite": s["last_date"], "Discipline": s["discipline"], "Objectif": s["target"]})
            stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)
            note("Ouvrez un client avec la liste « Ouvrir un client existant » de l'onglet « Fiche client ».")
        section("Image de marque des rapports", "Le nom et le logo de votre studio apparaissent sur les rapports PDF et HTML.")
        ss["studio"] = st.text_input("Nom du studio", value=ss["studio"], placeholder="ex. Cycles Dupont — Studio de fitting", key="studio_in")
        logo = st.file_uploader("Logo (PNG ou JPG)", type=["png", "jpg", "jpeg"], key="logo_up")
        if logo is not None:
            ss["logo_png"] = logo.getvalue()
        if ss["logo_png"]:
            st.image(ss["logo_png"], width=140)

if IS_ADMIN:
    with t_admin:
        auth_ui.admin_panel(user)

# ------------------------------------------------------------------------------
#  ANALYSE : étape 2 (prise de vue) puis étape 3 (résultats)
# ------------------------------------------------------------------------------
with t_main:
    step_box = st.empty()

    def show_steps(has_file, score=None, partial=False):
        step_box.markdown(ui_kit.stepper([
            ("Votre profil", profile_text(), "done"),
            ("Photo ou vidéo", "Importée" if has_file else "À importer ci-dessous", "done" if has_file else "now"),
            ("Résultats", f"Score{' partiel' if partial else ''} {score:.0f}/100" if score is not None else "Score, réglages, vélo 3D", "now" if score is not None else "todo"),
        ]), unsafe_allow_html=True)

    section("Étape 2 · Votre photo ou vidéo de profil", "Choisissez la source, puis importez le fichier. L'analyse démarre toute seule.", first=True)
    source = st.radio("Source", ["Photo", "Vidéo de pédalage", "Caméra"], horizontal=True, label_visibility="collapsed")
    photo_bytes = video_bytes = None
    if source == "Photo":
        up = st.file_uploader("Vue de profil (JPG ou PNG)", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        photo_bytes = up.getvalue() if up is not None else None
    elif source == "Vidéo de pédalage":
        up = st.file_uploader("Vidéo de profil (MP4, MOV, AVI) — 10 à 15 s de pédalage régulier", type=["mp4", "mov", "avi", "m4v"], label_visibility="collapsed")
        video_bytes = up.getvalue() if up is not None else None
    else:
        up = st.camera_input("Photo de profil", label_visibility="collapsed")
        photo_bytes = up.getvalue() if up is not None else None
    if source != "Vidéo de pédalage":
        st.radio("Comment la photo a-t-elle été prise ?", SHOT_MODES, horizontal=True, key="shot_mode",
                 help="Une jambe en mouvement est plus fléchie qu'une jambe posée : les angles visés pour le genou, la hanche et la cheville "
                      "ne sont pas les mêmes (25–35° de flexion du genou à l'arrêt, 30–40° en pédalant).")
    dynamic = source == "Vidéo de pédalage" or ss["shot_mode"] == SHOT_MODES[1]
    with st.expander("Options de prise de vue (côté visible, grille de cadrage)"):
        st.radio("Côté du cycliste visible sur l'image", ["Auto", "Droit", "Gauche"], horizontal=True, key="side_choice",
                 help="Laissez « Auto » : le côté le mieux visible est choisi automatiquement.")
        st.checkbox("Afficher une grille de cadrage sur l'image analysée", key="show_grid")

    if photo_bytes is None and video_bytes is None:
        ss["_analysis"] = None
        show_steps(False)
        landing()
        st.stop()

    # --- quota : une analyse est décomptée une seule fois par fichier et par compte
    _raw = video_bytes if video_bytes is not None else photo_bytes
    _ok, _why, _charged = acc.use_analysis(SC, hashlib.md5(_raw).hexdigest(), "vidéo" if video_bytes is not None else "photo")
    if not _ok:
        show_steps(True)
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
                show_steps(True)
                st.error(res["error"])
                st.stop()
            lms = [tuple(x) for x in res["lms_best"]]
            A.update(img=res["image"], lms=lms, side=res["side"], m=res["m"], source="vidéo", video=res)
        else:
            with st.spinner("Détection du squelette et calcul des angles…"):
                det = core.detect_image(photo_bytes)
            if det is None:
                show_steps(True)
                st.error("Impossible de détecter un corps sur cette image. Importez une vue latérale nette, bien éclairée et entièrement cadrée.")
                st.stop()
            lms = det["landmarks"]
            side = core.auto_side(lms) if ss["side_choice"] == "Auto" else ss["side_choice"]
            A.update(img=det["image"], lms=lms, side=side, source="photo" if source == "Photo" else "caméra", video=None)
    except RuntimeError as exc:
        show_steps(True)
        st.error(f"{exc}")
        st.stop()

    img = A["img"]
    ih, iw = img.shape[:2]
    pts, vis = core.side_points(A["lms"], A["side"], iw, ih)
    is_tt = core.is_aero(ss["discipline"])
    ranges = core.get_ranges(ss["discipline"], ctx_flex, ss["goal"], extra_shift, dynamic=dynamic)     # cibles selon photo posée / image en mouvement
    m = dict(A.get("m") or core.compute_metrics(pts, aero=is_tt))
    if A["video"] is None:
        m = core.compute_metrics(pts, aero=is_tt)
    elif is_tt:
        m["hip"] = core.hip_angle_bb(pts)             # prolongateurs : hanche mesurée vers le boîtier de pédalier (méthode F.I.S.T.)
    # --- la jambe est-elle au point mort bas ? Sinon genou, hanche et cheville ne sont pas jugés (une vidéo choisit elle-même le bon instant)
    crank = core.crank_check(A["lms"], A["side"], iw, ih) if A["video"] is None else None
    na_keys = core.BDC_KEYS if (crank and crank["state"] == "off") else ()
    ev = core.evaluate_all(m, ranges, na_keys)
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

    quality, qnotes, leg_tilt = core.assess_quality(A["lms"], vis, pts, iw, ih, img, crank=crank)
    rel_lvl, rel_txt = core.reliability(quality, crank)
    arm = core.aero_details(pts, core.is_facing_right(A["lms"], A["side"]))
    aero = core.aero_posture(m, arm["forearm_tilt"])            # avant-bras à l'horizontale : appui probable sur des prolongateurs
    tuck = core.tuck_posture(m, arm["forearm_tilt"])            # coudes très fléchis, mains plus basses : position de vitesse sur cintre classique
    recs = core.build_recommendations(m, ev, ranges, ctx)
    annotated = core.annotate(img, pts, m, ev, grid=ss["show_grid"])
    extras = []
    kops_for_bike = None
    ss["_analysis"] = True
    show_steps(True, gscore, partial=bool(na_keys))

    n_bad = sum(1 for r in recs if r["status"] == "bad")
    n_warn = sum(1 for r in recs if r["status"] == "warn")
    section("Étape 3 · Vos résultats", "Commencez par le résumé ; les autres rubriques détaillent chaque réglage, sans obligation de tout lire.")
    notice = ""
    if rel_lvl != "ok":
        reasons = [txt for lvl, txt in qnotes if lvl in ("bad", "warn")]
        if na_keys:
            notice = ("La manivelle n'est pas au point mort bas (6 h) sur cette photo : le genou, la hanche et la cheville ne sont pas évalués "
                      "et le score est partiel. Reprenez une photo de profil, pédale au plus bas.")
            H(ui_kit.banner("bad", "Photo à reprendre : la manivelle n'est pas à 6 h",
                            "Le genou, la hanche et la cheville ne se jugent que jambe en bas. Sur cette image ils ne sont <b>pas évalués</b> : "
                            "le score affiché est partiel (haut du corps seulement) et ne reflète pas la qualité réelle de la position.",
                            reasons, "Reprenez une photo de profil avec la pédale du côté de l'appareil au plus bas (6 h), ou filmez 10 à 15 s de pédalage : "
                                     "la vidéo choisit toute seule le bon instant."))
        elif rel_lvl == "bad":
            notice = "Prise de vue de qualité insuffisante : les mesures et le score de ce rapport sont peu fiables. Reprenez la photo."
            H(ui_kit.banner("bad", "Photo à reprendre : la mesure n'est pas fiable",
                            f"Qualité de la prise de vue : <b>{quality:.0f}/100</b>. Le score et les réglages proposés peuvent être faux.",
                            reasons, "Reprenez la photo : profil strict à 90° du vélo, corps entier dans le cadre, bonne lumière, manivelle à 6 h."))
        else:
            notice = "Prise de vue imparfaite : les mesures de ce rapport sont approximatives (quelques degrés d'écart possibles)."
            H(ui_kit.banner("warn", "Mesure approximative : prise de vue à améliorer",
                            f"Qualité de la prise de vue : <b>{quality:.0f}/100</b>. Les angles peuvent être décalés de quelques degrés : "
                            "confirmez avec une meilleure photo avant de modifier votre vélo.",
                            reasons, "Pour une mesure fiable : profil strict à 90° du vélo, corps entier dans le cadre, bonne lumière, manivelle à 6 h."))
    if aero and not is_tt:
        H(ui_kit.banner("warn", "Ce vélo a-t-il des prolongateurs ?",
                        "Le dos est très bas et les avant-bras sont à l'horizontale, comme sur un vélo de contre-la-montre ou de triathlon, "
                        "alors que le profil indique « " + _html.escape(ss["discipline"]) + " ». Si le vélo n'a pas de prolongateurs, ignorez ce message.",
                        [], f"S'il en a : choisissez « Contre-la-montre » ou « Triathlon » dans l'onglet « {PROFILE_TAB} ». "
                            "Sinon : pour régler un vélo de route, prenez plutôt la photo dans votre position habituelle, mains sur les cocottes."))
    elif tuck and not is_tt:
        H(ui_kit.banner("warn", "Position de recherche de vitesse : le score sous-estime ce réglage",
                        "Dos très bas et coudes très fléchis : c'est une position que l'on tient quelques minutes pour aller vite, pas la position de base du vélo. "
                        "Le tronc et les coudes sortent donc des cibles d'une position tenue des heures, ce qui fait baisser le score sans que le réglage soit en cause.",
                        [], "Pour juger le réglage du vélo, reprenez la photo dans votre position habituelle : mains sur les cocottes, bras souples. "
                            "Le genou, lui, reste valable sur cette image."))
    elif is_tt and not aero and m["elbow"] >= 140 and m["torso"] >= 32:
        H(ui_kit.banner("bad", "Photo à reprendre : le cycliste n'est pas sur les prolongateurs",
                        "Sur un vélo de contre-la-montre ou de triathlon, la position se mesure <b>avant-bras posés sur les accoudoirs, mains sur les prolongateurs</b>. "
                        "Ici les bras sont presque tendus et le dos relevé : le score ne reflète pas la position de course.",
                        [], f"Reprenez la photo en position aérodynamique. Si ce vélo n'a pas de prolongateurs, choisissez un autre type de vélo dans l'onglet « {PROFILE_TAB} »."))
    r_sum, r_bike, r_more, r_tools, r_follow, r_rep = st.tabs(
        ["Résumé", "Réglages du vélo", "Analyses complémentaires", "Simulateur & transfert", "Enregistrer & comparer", "Rapport"])

    # ==================================================================== RÉSUMÉ
    with r_sum:
        col_a, col_b = st.columns([0.95, 1.05], gap="large")
        with col_a:
            score_ring(gscore, partial=bool(na_keys))
            qcol = ui_kit.OK if quality >= 75 else (ui_kit.WARN if quality >= 55 else ui_kit.BAD)
            chips = []
            if n_bad:
                chips.append(f'<span class="chip" style="--c:{ui_kit.BAD}">{n_bad} à corriger</span>')
            if n_warn:
                chips.append(f'<span class="chip" style="--c:{ui_kit.WARN}">{n_warn} à surveiller</span>')
            if not n_bad and not n_warn:
                chips.append(f'<span class="chip" style="--c:{ui_kit.OK}">{"Angles mesurés dans la cible" if na_keys else "Tous les angles dans la cible"}</span>')
            if na_keys:
                chips.append(f'<span class="chip" style="--c:{ui_kit.MUT}">{len(na_keys)} non mesurables</span>')
            chips.append(f'<span class="chip" style="--c:{ui_kit.BAD if rel_lvl == "bad" else (ui_kit.WARN if rel_lvl == "warn" else ui_kit.OK)}">{rel_txt} · prise de vue {quality:.0f}/100</span>')
            H('<div class="sum-chips">' + "".join(chips) + "</div>")
            st.caption(f"Score sur 100 : moyenne pondérée {'des angles mesurables' if na_keys else 'de six angles'}, comparés aux plages visées pour « {ss['discipline']} », objectif {ss['goal'].lower()}, "
                       f"souplesse {ctx_flex.lower()}.")
        with col_b:
            stretch(st.image, annotated, caption=f"Côté analysé : {A['side']} · {ss['discipline']} · source : {A['source']}")

        next_box = st.container()      # « par où commencer » : rempli plus bas, avec le premier réglage de la liste
        section("Les réglages à faire sur votre vélo", "Chaque numéro du vélo correspond à une ligne de la liste. Le détail de chaque réglage se trouve dans la rubrique « Réglages du vélo ».")
        bike_box = st.container()      # rempli plus bas, une fois le recul de selle (photo à 3 h) connu

        section("Vos 6 angles mesurés", "La zone verte de chaque jauge est la plage visée pour votre profil ; le trait indique votre mesure.")
        st.caption(("Cibles pour une image prise en pédalant" if dynamic else "Cibles pour une photo posée, à l'arrêt") + f" · « {ss['discipline']} ». "
                   "Précision de la mesure : environ ± 5° par angle ; un écart de 2 ou 3° n'est pas significatif. "
                   + ("La hanche est mesurée vers le pédalier (méthode F.I.S.T.). " if is_tt else "")
                   + "Sources détaillées dans l'onglet « Guide ».")
        c1, c2, c3 = st.columns(3)
        for i, k in enumerate(ORDER):
            with (c1, c2, c3)[i % 3]:
                metric_card(k, m[k], ev[k], ranges[k])

        section("Pour aller plus loin", "Vue d'ensemble des six angles, fiabilité de la mesure et calibration.")
        a, b = st.columns([0.9, 1.1], gap="large")
        with a:
            st.markdown("##### Profil postural")
            stretch(st.plotly_chart, radar(scores))
            if na_keys:
                st.caption("Genou, hanche et cheville apparaissent à zéro sur ce graphique : ils ne sont pas mesurables sur cette photo.")
        with b:
            st.markdown("##### Fiabilité de la mesure")
            for lvl, txt in qnotes:
                H(f'<div class="insight" style="--c:{STATUS[lvl][0]}"><p style="margin:0">{txt}</p></div>')
            if ss["learn"]:
                with st.expander("Comment lire ces résultats ?"):
                    st.write("Chaque angle est comparé à une plage cible. En vert : dans la cible. En orange : écart modéré. En rouge : écart important. Le score est une moyenne pondérée : le genou compte le plus (30 %), car c'est le réglage le plus déterminant.")
                    st.write(f"Votre plage cible dépend de la discipline ({ss['discipline']}), de votre objectif ({ss['goal']}) et de votre souplesse ({ctx_flex}).")
            with st.expander("Calibration (optionnelle)"):
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
        note("Les plages cibles sont indicatives et issues des pratiques courantes de bike-fitting. Elles ne remplacent ni un fitting en studio avec capture dynamique, ni l'avis d'un professionnel de santé en cas de douleur persistante.")

    # ==================================================================== RÉGLAGES DU VÉLO
    with r_bike:
        st.caption("Le détail de chaque réglage : ce qui a été mesuré, pourquoi cela compte et comment corriger.")
        t_sel, t_tro, t_mat = st.tabs(["Selle & recul", "Tronc & cockpit", "Cales, pneus & matériel"])

        # --- selle & recul
        with t_sel:
            for r in recs:
                if r["key"] in ("knee", "ankle"):
                    insight(r)
            section("Recul de selle (KOPS)", "Pour mesurer le recul, photographiez le cycliste avec la manivelle à l'horizontale (3 h, pédale avant) et importez la photo ici. "
                                             "À défaut, l'image principale est utilisée si la jambe est dans la bonne position.")
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
                    kops_for_bike = kres
                st.caption("L'axe de pédale est estimé à partir de la position du pied (≈ 72 % entre talon et orteil) : mesure indicative.")
            section("Hauteur de selle de référence", "Des formules classiques donnent un point de départ ; la mesure par l'angle du genou est plus fiable pour affiner.")
            if ctx["inseam"] > 0:
                e = ctx["inseam"]
                x1, x2, x3 = st.columns(3)
                x1.metric("Pédale en bas → dessus de selle", f"{e * 1.06:.1f} à {e * 1.09:.1f} cm", help="106 à 109 % de l'entrejambe : la plage classique, mesurée de l'axe de pédale au point bas jusqu'au dessus de la selle.")
                x2.metric("Même mesure, étude de 2012", f"{e * 1.086:.1f} à {e * 1.104:.1f} cm", help="108,6 à 110,4 % de l'entrejambe : plage qui donne 30 à 40° de flexion du genou en pédalant chez des cyclistes entraînés (Ferrer-Roca et al., 2012).")
                x3.metric("Pédalier → dessus de selle (LeMond)", f"{e * 0.883:.1f} cm", help="0,883 × entrejambe, mesuré depuis l'axe du boîtier de pédalier. Repère historique.")
                st.caption("Ces formules donnent un point de départ. Dans l'étude de Ferrer-Roca et al. (2012), plus de la moitié des cyclistes de haut niveau étaient hors de la plage 106–109 % "
                           "tout en ayant un angle de genou correct : c'est l'angle du genou qui tranche.")
            else:
                st.info("Renseignez votre entrejambe dans l'onglet « Mon profil » pour afficher les hauteurs de selle de référence (LeMond, Hamley).")
            d_now = core.hip_ankle_dist(m["knee"], seg)
            y1, y2 = st.columns(2)
            y1.metric("Distance hanche → cheville", f"{d_now / 10:.1f} cm", help="Estimée avec votre calibration ou un modèle anthropométrique.")
            y2.metric("Inclinaison de la jambe", f"{leg_tilt:.0f}°", help="Écart de l'axe hanche-cheville par rapport à la verticale (≈ 6 h si < 30°).")

        # --- tronc & cockpit
        with t_tro:
            for r in recs:
                if r["key"] in ("torso", "hip", "shoulder", "elbow"):
                    insight(r)
            if is_tt:
                ad = core.aero_details(pts, core.is_facing_right(A["lms"], A["side"]))
                section("Appuis sur les prolongateurs", "Deux repères propres aux vélos de contre-la-montre et de triathlon. Ce sont des repères de pratique, sans norme publiée : ils n'entrent pas dans le score.")
                q1, q2 = st.columns(2)
                ft, ua = ad["forearm_tilt"], ad["upper_arm_fwd"]
                q1.metric("Inclinaison des avant-bras", f"{ft:+.0f}°", help="0° = avant-bras horizontaux ; valeur positive = mains plus hautes que les coudes.")
                q1.caption("Repère usuel : de l'horizontale à environ 15° vers le haut. " + ("Dans le repère." if 0 <= ft <= 20 else
                           ("Mains nettement plus basses que les coudes : le poids glisse vers l'avant, relevez l'extrémité des prolongateurs." if ft < 0 else
                            "Mains très hautes : position stable, à comparer au règlement de votre fédération si vous courez.")))
                q2.metric("Coude par rapport à l'épaule", f"{ua:+.0f}°", help="0° = bras vertical (coude sous l'épaule) ; valeur positive = coude en avant de l'épaule.")
                q2.caption("Repère usuel : coude sous l'épaule ou jusqu'à 15° en avant, pour s'appuyer sur le squelette et non sur les muscles. " + ("Dans le repère." if -3 <= ua <= 18 else
                           ("Coude en arrière de l'épaule : avancez les accoudoirs." if ua < -3 else "Coude loin devant l'épaule : reculez les accoudoirs.")))
                extras.append(("Appuis sur les prolongateurs", f"Avant-bras inclinés de {ft:+.0f}° (repère : 0 à 15° vers le haut) ; coude à {ua:+.0f}° de la verticale de l'épaule (repère : 0 à 15° en avant)."))
            if is_tt:
                note("Sur un vélo à prolongateurs, le cockpit se règle par la hauteur des accoudoirs (cales sous les appuis), leur avance, et la longueur et l'inclinaison des prolongateurs. "
                     "Réglez d'abord la hanche (selle), puis descendez les accoudoirs par pas de 5 à 10 mm.")
            else:
                note("Le cockpit se règle avec la potence (longueur, angle) et la hauteur du cintre. Relever le cintre de 10 mm modifie le tronc d'environ 1 à 2°. Ajustez par pas de 10 mm et testez le simulateur avant de modifier votre vélo.")

        # --- cales, pneus & matériel
        with t_mat:
            section("Longueur de manivelle et largeur de cintre", "Repères calculés depuis votre entrejambe et votre largeur d'épaules.", first=True)
            z1, z2 = st.columns(2)
            with z1:
                if ctx["inseam"] > 0:
                    best, raw = core.crank_length_suggestion(ctx["inseam"])
                    st.metric("Manivelle conseillée", f"{core.fr_num(best)} mm", help=f"Environ 21,6 % de l'entrejambe ({raw:.0f} mm), arrondie au format standard.")
                    st.caption("Un écart de 2,5 mm n'a pas d'effet mesurable ; au-delà de 5 mm, adaptez aussi la hauteur de selle.")
                else:
                    st.info("Renseignez l'entrejambe dans « Mon profil » pour une suggestion de manivelle.")
            with z2:
                if ss["shoulder_w"] > 0:
                    st.metric("Largeur de cintre conseillée", f"{core.bar_width_suggestion(ss['shoulder_w'])} cm", help="Proche de la largeur de vos épaules, mesurée entre les points osseux.")
                    st.caption("Un cintre plus large ouvre la cage thoracique ; plus étroit, il est plus aérodynamique mais moins stable.")
                else:
                    st.info("Renseignez la largeur d'épaules dans « Mon profil » pour une suggestion de cintre.")
            section("Pression des pneus", "Point de départ calculé depuis votre poids et le type de vélo.")
            tp = core.tyre_pressure(ss["discipline"], ctx["weight"])
            if tp:
                t1, t2, t3 = st.columns(3)
                t1.metric("Pneu avant", f"{core.fr_num(tp['front'])} bar")
                t2.metric("Pneu arrière", f"{core.fr_num(tp['rear'])} bar")
                t3.metric("Poids cycliste + vélo", f"{tp['system']:.0f} kg", help=f"{ctx['weight']} kg + un vélo type d'environ {core.fr_num(tp['bike'])} kg.")
                note(f"Valeurs indicatives pour des pneus de {tp['tyre']} avec chambre à air. En tubeless, retirez 0,3 à 0,5 bar ; sur route mouillée ou terrain meuble, baissez encore un peu. "
                     "Ne dépassez jamais la pression maximale inscrite sur le pneu et sur la jante.")
            else:
                st.info("Renseignez votre poids dans « Mon profil » pour obtenir une pression de départ.")
            section("Cales et pied")
            ank = next(r for r in recs if r["key"] == "ankle")
            insight(ank)
            card("warn" if ev["ankle"]["dir"] != "in" else "ok", "Réglage des cales — points de contrôle",
                 "La photo ne permet pas de mesurer directement les cales. Voici la procédure de contrôle :",
                 ["<b>Avant-arrière</b> : l'articulation du gros orteil à l'aplomb de l'axe de pédale. Plus en avant, la charge sur le mollet augmente ; plus en arrière, elle diminue.",
                  "<b>Rotation</b> : laissez le pied pivoter naturellement ; une rotation forcée sollicite le genou.",
                  "<b>Écartement</b> : réglez pour que les genoux restent alignés avec les hanches (voir Analyses complémentaires › Vue de face).",
                  "Ajustez une seule cale à la fois, par petits pas de 1 à 2 mm.", "Consultez un fitter si vous avez des douleurs de genou ou de pied persistantes."])
            section("Conseils pour votre discipline")
            for tip in core.DISCIPLINE_TIPS[ss["discipline"]]:
                st.markdown(f"- {tip}")
            note("Les cales, la selle (largeur, inclinaison) et le cintre (forme, reach) influencent beaucoup le confort. Les mesurer précisément demande un outil dédié : cette app donne des repères, pas un diagnostic.")

    # ==================================================================== ANALYSES COMPLÉMENTAIRES
    with r_more:
        st.caption("Trois analyses facultatives pour compléter le profil : symétrie vue de face, pédalage en vidéo, mobilité et douleurs.")
        t_front, t_ped, t_mob = st.tabs(["Vue de face", "Pédalage (vidéo)", "Mobilité & douleurs"])

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
                st.info("L'analyse dynamique est disponible avec une vidéo : à l'étape 2, choisissez « Vidéo de pédalage ». Filmez 10 à 15 secondes de pédalage régulier, de profil, sur home-trainer.")
            else:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Cadence", f"{vr['cadence']:.0f} tr/min")
                k2.metric("Genou au point bas", f"{vr['knee_max']:.1f}°")
                k3.metric("Genou au point haut", f"{vr['knee_min']:.0f}°" if not np.isnan(vr["knee_min"]) else "—")
                k4.metric("Régularité", f"±{vr['bdc_std']:.1f}°")
                fig = go.Figure()
                fig.add_hrect(y0=ranges["knee"][0], y1=ranges["knee"][1], fillcolor="rgba(52,211,153,.14)", line_width=0)
                fig.add_trace(go.Scatter(x=vr["times"], y=vr["knee"], mode="lines", name="Angle du genou", line=dict(color="#c6f432", width=3)))
                fig.add_trace(go.Scatter(x=[vr["times"][i] for i in vr["bdc"]], y=[vr["knee"][i] for i in vr["bdc"]], mode="markers", name="Point bas",
                                         marker=dict(size=10, color="#fb7185")))
                fig.add_trace(go.Scatter(x=[vr["times"][i] for i in vr["top"]], y=[vr["knee"][i] for i in vr["top"]], mode="markers", name="Point haut",
                                         marker=dict(size=10, color="#5ec8ff")))
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=330, margin=dict(l=10, r=10, t=10, b=10), font=dict(color="#c9d2de"),
                                  xaxis=dict(title="Temps (s)", gridcolor="rgba(255,255,255,.07)"), yaxis=dict(title="Genou (°)", gridcolor="rgba(255,255,255,.07)"),
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
            section("Questionnaire de mobilité", "Réalisez ces tests simples. Cochez « Affiner la souplesse avec le questionnaire de mobilité » dans « Mon profil » "
                                                 "pour que vos résultats ajustent les plages cibles.", first=True)
            for t in core.MOBILITY_TESTS:
                st.radio(t["title"], t["options"], key="mob_" + t["key"], horizontal=True, help=t["help"])
            prof = core.mobility_profile(mobility_answers())
            mc1, mc2 = st.columns(2)
            mc1.metric("Score de mobilité", f"{prof['score']:.0f}/100")
            mc2.metric("Profil de souplesse", prof["flex_label"])
            if not ss["use_mob"]:
                st.info("Ces résultats ne modifient pas encore les plages cibles : activez l'option dans l'onglet « Mon profil ».")
            else:
                st.success(f"Plages cibles ajustées : tronc {prof['shifts']['torso']:+d}°, hanche {prof['shifts']['hip']:+d}°, épaule {prof['shifts']['shoulder']:+d}°.")
            for lvl, title, txt in prof["notes"]:
                card(lvl, title, txt, tag="Exercice conseillé")
            if prof["notes"]:
                extras.append(("Mobilité — exercices", " ; ".join(f"{t} : {x}" for _, t, x in prof["notes"][:3])))
            section("Douleurs et mesures", "Vos douleurs déclarées sont rapprochées des angles mesurés sur cette analyse.")
            if not ss["complaints"]:
                st.info("Indiquez vos douleurs dans l'onglet « Mon profil » pour les rapprocher des mesures de cette analyse.")
            pains = core.pain_analysis(ss["complaints"], ev)
            for lvl, name, txt in pains:
                card(lvl, name, txt, tag="Lien probable" if lvl == "bad" else "Pas de lien direct")
            if pains:
                extras.append(("Douleurs signalées", " ; ".join(f"{n} ({'lien probable' if l == 'bad' else 'pas de lien direct'})" for l, n, _ in pains)))
                note("Une douleur persistante doit être évaluée par un professionnel de santé. Cet outil propose des pistes de réglage, pas un diagnostic.")

    # ==================================================================== SIMULATEUR & TRANSFERT
    with r_tools:
        st.caption("Deux outils : tester l'effet d'un réglage avant de toucher au vélo, et reporter vos réglages sur un autre vélo.")
        t_sim, t_tr = st.tabs(["Simulateur de réglage", "Transfert vers un autre vélo"])

        # --- simulateur
        with t_sim:
            section("Simulez un réglage avant de le faire", "Déplacez les curseurs : le score et les angles estimés se mettent à jour.", first=True)
            s1, s2 = st.columns(2, gap="large")
            with s1:
                d_sel = st.slider("Hauteur de selle (mm)", -30, 30, 0, 1, help="Positif = monter la selle")
            with s2:
                d_bar = st.slider("Hauteur de cintre (mm)", -40, 40, 0, 1, help="Positif = relever le cintre")
            new = dict(m)
            new["knee"] = core.knee_after_delta(m["knee"], d_sel, seg)
            new["torso"] = core.torso_after_bar_delta(m["torso"], d_bar, ctx["height"])
            new["hip"] = m["hip"] + (new["torso"] - m["torso"])
            ev_new = core.evaluate_all(new, ranges, na_keys)
            if na_keys:
                st.warning("La manivelle n'est pas à 6 h sur cette photo : l'effet de la hauteur de selle sur le genou ne peut pas être simulé de façon fiable. "
                           "Seul l'effet de la hauteur du cintre sur le tronc est pris en compte dans le score.")
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
            section("Transférer vos réglages d'un vélo à un autre", "Mesurez votre vélo de référence (celui sur lequel vous êtes bien) et le nouveau vélo, puis obtenez la liste des ajustements à faire.", first=True)
            ref, cur = {}, {}
            ca, cb = st.columns(2, gap="large")
            ca.markdown("**Vélo de référence**")
            cb.markdown("**Nouveau vélo**")
            for key, label, helptxt, default in core.TRANSFER_FIELDS:
                va = ca.number_input(label, value=float(default), step=1.0, key=f"tr_ref_{key}", help=helptxt or None)
                vb = cb.number_input(label, value=float(default), step=1.0, key=f"tr_cur_{key}", help=helptxt or None)
                ref[key], cur[key] = va, vb
            plan = core.transfer_plan(ref, cur)
            section("Ajustements à effectuer")
            for p in plan:
                card(p["status"], p["label"], f"Référence : <b>{p['ref']:g}</b> · Nouveau vélo : <b>{p['cur']:g}</b>", [p["action"]], tag="À régler" if p["status"] != "ok" else "OK")
            note("L'ordre conseillé : manivelle, hauteur de selle, recul, puis allonge et dénivelé du cockpit. Terminez par une nouvelle analyse posturale pour valider.")

    # ==================================================================== SUIVI
    with r_follow:
        section(f"Enregistrer cette analyse — {active}", "Donnez-lui un nom pour la retrouver et comparer l'avant / après de vos réglages.", first=True)
        if rel_lvl == "bad":
            st.warning("Cette analyse n'est pas fiable (voir l'avertissement en haut des résultats) : mieux vaut reprendre la photo avant de l'enregistrer dans votre suivi.")
        cur_dict = dict(m=m, score=gscore, annotated=annotated, source=A["source"], quality=quality, ev=ev,
                        extra={**(dict(cadence=round(A["video"]["cadence"], 1), rom=round(A["video"]["rom"], 1)) if A["video"] and not np.isnan(A["video"]["rom"]) else {}),
                               **({"partial": True} if na_keys else {}), **({"dynamic": True} if dynamic else {})})
        history_section(active, cur_dict, kp="an_")

    # ==================================================================== RAPPORT
    with r_rep:
        section("Rapport personnalisé", "Un document à garder ou à transmettre : score, image annotée, mesures et plan d'action.", first=True)
        r1, r2 = st.columns(2)
        studio_name = r1.text_input("Nom du studio / de la marque", value=ss["studio"] if fitter else "", key="rep_studio", placeholder="VeloFit AI Studio")
        client_name = r2.text_input("Nom du cycliste", value=active if active != "Invité" else "", key="rep_client")
        logo_file = st.file_uploader("Logo (optionnel)", type=["png", "jpg", "jpeg"], key="rep_logo")
        logo_bytes = logo_file.getvalue() if logo_file is not None else (ss["logo_png"] if fitter else None)
        rep = core.assemble_report(ctx, m, ev, ranges, gscore, recs, quality, annotated, studio=studio_name, client=client_name, logo_bytes=logo_bytes, extras=extras, notice=notice)
        b1, b2, b3 = st.columns(3)
        if b1.button("Générer le PDF", key="mk_pdf", type="primary"):
            with st.spinner("Création du PDF…"):
                ss["_pdf"] = core.report_pdf(rep)
        if ss.get("_pdf"):
            b1.download_button("Télécharger le PDF", ss["_pdf"], "velofit_rapport.pdf", "application/pdf", key="dl_pdf")
        b2.download_button("Rapport HTML (imprimable)", core.report_html(rep).encode("utf-8"), "velofit_rapport.html", "text/html", key="dl_html")
        b3.download_button("Rapport Markdown", core.report_markdown(rep).encode("utf-8"), "velofit_rapport.md", "text/markdown", key="dl_md")
        df_m = pd.DataFrame([{"Mesure": META[k]["label"], "Valeur (°)": round(m[k], 1), "Cible min": ranges[k][0], "Cible max": ranges[k][1],
                              "Statut": STATUS[ev[k]["status"]][1], "Score": round(scores[k])} for k in ORDER])
        e1, e2 = st.columns(2)
        e1.download_button("Image annotée (PNG)", core.png_bytes(annotated), "velofit_analyse.png", "image/png", key="dl_png")
        e2.download_button("Mesures (CSV)", df_m.to_csv(index=False).encode("utf-8"), "velofit_mesures.csv", "text/csv", key="dl_csv")
        note("Le PDF reprend le score, l'image annotée, les mesures, le plan d'action et les sections complétées dans les autres rubriques (recul de selle, vue de face, pédalage, douleurs, mobilité).")

    # --- vélo 3D du résumé : construit en dernier pour tenir compte du recul de selle mesuré plus haut
    adjustments = core.bike_adjustments(m, ev, ranges, ctx, kops_for_bike)
    with next_box:
        first_adj = next((a for a in adjustments if a["status"] in ("bad", "warn")), None)
        if rel_lvl == "bad":
            H(ui_kit.cta("Par où commencer : reprendre la photo", "Cette image ne permet pas une mesure fiable. Ne modifiez pas votre vélo sur la base de ces résultats : "
                                                                  "reprenez d'abord une photo de profil, manivelle à 6 h, ou une courte vidéo."))
        elif first_adj:
            H(ui_kit.cta(f"Par où commencer : {first_adj['title'][0].lower() + first_adj['title'][1:]}",
                         " · ".join(_html.escape(x) for x in first_adj["reasons"])
                         + ". Faites ce réglage seul, roulez, puis reprenez une photo pour vérifier avant de passer au suivant."))
        else:
            H(ui_kit.cta("Votre position est dans la cible", "Aucun réglage prioritaire. Enregistrez cette analyse pour garder une référence, "
                                                              "et refaites un contrôle après tout changement de matériel."))
    with bike_box:
        bike_view(adjustments)
