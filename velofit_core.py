# ==============================================================================
#  velofit_core.py — logique métier de VeloFit AI Studio (aucune dépendance Streamlit)
#  Vision, biomécanique, vidéo, calibration, mobilité, stockage et rapports.
# ==============================================================================
from __future__ import annotations

import base64
import html as _html
import io
import json
import math
import os
import re
import tempfile
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# ------------------------------------------------------------------------------
#  CONSTANTES
# ------------------------------------------------------------------------------
IDX = dict(
    NOSE=0, LEFT_SHOULDER=11, RIGHT_SHOULDER=12, LEFT_ELBOW=13, RIGHT_ELBOW=14,
    LEFT_WRIST=15, RIGHT_WRIST=16, LEFT_HIP=23, RIGHT_HIP=24, LEFT_KNEE=25,
    RIGHT_KNEE=26, LEFT_ANKLE=27, RIGHT_ANKLE=28, LEFT_HEEL=29, RIGHT_HEEL=30,
    LEFT_FOOT_INDEX=31, RIGHT_FOOT_INDEX=32,
)
NAMES = ["SHOULDER", "ELBOW", "WRIST", "HIP", "KNEE", "ANKLE", "HEEL", "FOOT_INDEX"]

STATUS = {
    "ok": ("#34d399", "Optimal"),
    "warn": ("#fbbf24", "À surveiller"),
    "bad": ("#fb7185", "À corriger"),
}

FLEX_SHIFT = {"Limitée": 5, "Moyenne": 0, "Très souple": -4}
GOAL_SHIFT = {"Confort": 4, "Équilibré": 0, "Performance": -4}

# Plages cibles (min, max) en degrés — indicatives, issues des pratiques courantes de bike-fitting.
BASE_RANGES = {
    "Route / Endurance": dict(knee=(145, 155), torso=(42, 55), hip=(112, 135), shoulder=(80, 100), elbow=(150, 170), ankle=(95, 120)),
    "Compétition / Course": dict(knee=(142, 152), torso=(28, 42), hip=(95, 115), shoulder=(75, 95), elbow=(140, 165), ankle=(95, 120)),
    "Gravel": dict(knee=(143, 153), torso=(40, 52), hip=(105, 128), shoulder=(80, 100), elbow=(150, 168), ankle=(95, 120)),
    "VTT / XC": dict(knee=(145, 155), torso=(38, 50), hip=(105, 128), shoulder=(78, 98), elbow=(145, 168), ankle=(95, 120)),
    "Triathlon / CLM": dict(knee=(143, 153), torso=(8, 22), hip=(80, 105), shoulder=(85, 110), elbow=(80, 110), ankle=(95, 120)),
}

META = {
    "knee": dict(label="Genou · point mort bas", short="Genou", icon="🦵", w=0.30, tol=8, vmin=110, vmax=180),
    "torso": dict(label="Inclinaison du tronc", short="Tronc", icon="📐", w=0.20, tol=10, vmin=0, vmax=80),
    "hip": dict(label="Ouverture de hanche", short="Hanche", icon="🔓", w=0.15, tol=12, vmin=60, vmax=150),
    "shoulder": dict(label="Angle d'épaule", short="Épaule", icon="💪", w=0.15, tol=12, vmin=50, vmax=120),
    "elbow": dict(label="Angle du coude", short="Coude", icon="🦾", w=0.10, tol=12, vmin=60, vmax=180),
    "ankle": dict(label="Cheville", short="Cheville", icon="🦶", w=0.10, tol=12, vmin=70, vmax=140),
}
ORDER = ["knee", "torso", "hip", "shoulder", "elbow", "ankle"]

COMPLAINTS = {
    "Genou — douleur à l'avant": [("knee", "low")],
    "Genou — douleur à l'arrière": [("knee", "high")],
    "Bas du dos / lombaires": [("torso", "low"), ("hip", "low")],
    "Nuque / cervicales": [("torso", "low")],
    "Mains / poignets engourdis": [("shoulder", "high"), ("torso", "low")],
    "Épaules / trapèzes": [("elbow", "high"), ("shoulder", "high")],
    "Selle / périnée": [("knee", "high"), ("hip", "low")],
    "Pieds / orteils": [("ankle", "high"), ("ankle", "low")],
}

DISCIPLINE_TIPS = {
    "Route / Endurance": [
        "Visez le confort sur 3 à 6 h : un tronc relevé et des coudes légèrement fléchis limitent les douleurs.",
        "Privilégiez une potence plutôt courte et un cintre pas trop bas, surtout si la souplesse est limitée.",
        "Vérifiez la largeur de cintre : elle doit correspondre à la largeur de vos épaules.",
    ],
    "Compétition / Course": [
        "Une position basse n'est utile que si elle est tenable : mieux vaut 5 % de watts en plus qu'une position trop agressive.",
        "Travaillez la gaine abdominale et la mobilité des ischio-jambiers pour tenir le tronc bas sans cambrer.",
        "Refaites un contrôle après chaque changement de potence ou d'entretoises.",
    ],
    "Gravel": [
        "Un cockpit un peu plus relevé et large améliore le contrôle sur terrain irrégulier.",
        "Gardez les coudes souples : ils servent d'amortisseurs sur les passages techniques.",
        "Prévoyez une selle légèrement plus basse si vous roulez souvent en descente technique (compromis de 3 à 5 mm).",
    ],
    "VTT / XC": [
        "Sur un VTT, le recul de selle et la hauteur du cintre pèsent plus que l'aérodynamisme.",
        "Une tige de selle télescopique permet de garder une hauteur optimale à la montée.",
        "Vérifiez que le tronc reste assez relevé pour garder du poids sur la roue avant en montée raide.",
    ],
    "Triathlon / CLM": [
        "Sur prolongateurs, les coudes sont fléchis à 80–110° : c'est normal et recherché pour l'aérodynamisme.",
        "Une hanche plus ouverte que la cible limite la respiration et la puissance : l'avant du bassin doit pouvoir basculer.",
        "La selle est souvent plus avancée qu'à vélo de route : contrôlez le recul à 3 h dans l'onglet dédié.",
    ],
}

METRIC_WHY = {
    "knee": "C'est le réglage le plus important : il décide de l'efficacité de chaque coup de pédale et protège vos genoux.",
    "torso": "L'inclinaison du buste influence le confort du dos et de la nuque, mais aussi la résistance à l'air.",
    "hip": "L'ouverture de hanche conditionne la respiration, la liberté du bassin et les douleurs lombaires.",
    "shoulder": "Cet angle traduit la distance entre vos épaules et le guidon : trop long, les mains et épaules fatiguent.",
    "elbow": "Des coudes souples absorbent les vibrations ; des bras tendus ou trop fléchis fatiguent épaules et poignets.",
    "ankle": "La cheville reflète la position du pied sur la pédale et peut trahir une selle ou des cales mal placées.",
}

GLOSSARY_TERMS = [
    ("Point mort bas (PMB)", "Position où la pédale est au plus bas (manivelle à 6 h). Le genou y est le plus étendu : c'est là qu'on règle la hauteur de selle."),
    ("Angle du genou", "Angle intérieur entre la cuisse et la jambe. Plus il est proche de 180°, plus la jambe est tendue."),
    ("Recul de selle", "Distance horizontale entre la pointe de la selle et l'axe du boîtier de pédalier. Un recul adapté équilibre le poids entre selle et mains."),
    ("KOPS", "« Knee Over Pedal Spindle » : repère selon lequel le genou doit se trouver à la verticale de l'axe de pédale quand la manivelle est horizontale. Point de départ, pas une règle absolue."),
    ("Allonge (reach)", "Distance entre la selle et le guidon. Elle se règle surtout avec la longueur de potence."),
    ("Dénivelé (drop)", "Différence de hauteur entre le dessus de la selle et le cintre. Plus il est grand, plus la position est basse."),
    ("Potence / entretoises", "La potence relie le cintre à la fourche ; les entretoises (spacers) sous la potence servent à régler la hauteur du cintre."),
    ("Cales", "Pièces fixées sous la chaussure qui l'accrochent à la pédale. Leur position avant-arrière, leur rotation et leur écartement influencent genoux et pieds."),
    ("Valgus / varus", "Le genou part vers l'intérieur (valgus) ou vers l'extérieur (varus) pendant le pédalage, vu de face."),
    ("Q-factor", "Écartement entre les deux pédales. Un Q-factor mal adapté peut surcharger genoux et hanches."),
    ("ROM (amplitude)", "Écart entre l'angle maximal et minimal du genou sur un tour de pédale."),
]

# ------------------------------------------------------------------------------
#  QUESTIONNAIRE DE MOBILITÉ
# ------------------------------------------------------------------------------
MOBILITY_TESTS = [
    dict(key="hamstring", title="Toucher les orteils", help="Debout, jambes tendues, penchez-vous lentement en avant.",
         options=["Genoux", "Mi-tibias", "Orteils", "Paumes au sol"]),
    dict(key="hip_flexor", title="Flexibilité de la hanche (test de Thomas)",
         help="Allongé au bord d'une table, ramenez un genou contre la poitrine : comment se comporte l'autre cuisse ?",
         options=["Reste nettement relevée", "Légèrement relevée", "Se pose à plat"]),
    dict(key="shoulder", title="Mobilité des épaules", help="Une main passe par-dessus l'épaule, l'autre dans le dos par-dessous.",
         options=["Impossible", "Bout des doigts", "Les mains se touchent"]),
    dict(key="ankle", title="Mobilité de la cheville (genou au mur)", help="Pied face à un mur : distance maximale du gros orteil au mur en touchant le mur avec le genou.",
         options=["Moins de 5 cm", "5 à 10 cm", "Plus de 10 cm"]),
    dict(key="lumbar", title="Gêne lombaire en flexion avant", help="Ressentez-vous une tension ou une douleur dans le bas du dos ?",
         options=["Souvent", "Parfois", "Jamais"]),
]

_MOB_SHIFTS = {
    "hamstring": ("torso", [5, 2, 0, -3]),
    "lumbar": ("torso", [3, 1, 0]),
    "hip_flexor": ("hip", [6, 3, 0]),
    "shoulder": ("shoulder", [-4, -2, 0]),
}

EXERCISES = {
    "hamstring": "Étirement des ischio-jambiers : 3 × 30 s par jambe, jambe tendue sur un support, dos droit. Ajoutez des « good mornings » légers.",
    "hip_flexor": "Étirement du psoas en fente basse : 3 × 30 s par côté, bassin basculé vers l'arrière, fessier contracté.",
    "shoulder": "Mobilité d'épaules : rotations avec un bâton ou un élastique, 2 × 10 répétitions, et étirement des pectoraux dans l'encadrement d'une porte.",
    "ankle": "Mobilité de cheville : genou au mur 2 × 10 répétitions par côté, et étirement des mollets.",
    "lumbar": "Gainage et mobilité lombaire : planche 3 × 30 s, chat-vache 2 × 10, et consultez un professionnel si la douleur persiste.",
}


def mobility_profile(answers: dict) -> dict:
    """Transforme les réponses du questionnaire en profil de souplesse et décalages de plages."""
    total, maxi = 0, 0
    shifts = {"torso": 0, "hip": 0, "shoulder": 0}
    notes = []
    for t in MOBILITY_TESTS:
        n = len(t["options"])
        idx = int(answers.get(t["key"], n // 2))
        idx = max(0, min(n - 1, idx))
        total += idx
        maxi += n - 1
        if t["key"] in _MOB_SHIFTS:
            target, table = _MOB_SHIFTS[t["key"]]
            shifts[target] += table[idx]
        if idx == 0:
            notes.append(("bad", t["title"], EXERCISES[t["key"]]))
        elif idx < n - 1:
            notes.append(("warn", t["title"], EXERCISES[t["key"]]))
    score = 100.0 * total / maxi if maxi else 50.0
    flex = "Limitée" if score < 40 else ("Moyenne" if score < 70 else "Très souple")
    return {"score": score, "flex_label": flex, "shifts": shifts, "notes": notes}


def get_ranges(discipline, flexibility="Moyenne", goal="Équilibré", extra=None):
    """Plages cibles ajustées selon la souplesse, l'objectif et un éventuel décalage par zone."""
    r = {k: tuple(v) for k, v in BASE_RANGES[discipline].items()}
    shift = FLEX_SHIFT.get(flexibility, 0) + GOAL_SHIFT.get(goal, 0)
    extra = extra or {}
    t = shift + extra.get("torso", 0)
    h = shift + extra.get("hip", 0)
    s = extra.get("shoulder", 0)
    r["torso"] = (r["torso"][0] + t, r["torso"][1] + t)
    r["hip"] = (r["hip"][0] + h, r["hip"][1] + h)
    r["shoulder"] = (r["shoulder"][0] + s, r["shoulder"][1] + s)
    return r


# ------------------------------------------------------------------------------
#  DÉTECTION DE POSE (compatible anciennes et nouvelles versions de mediapipe)
# ------------------------------------------------------------------------------
_LOCK = threading.Lock()
_STATIC = {"backend": None}
_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/{name}/float16/latest/{name}.task"


class _LegacyBackend:
    def __init__(self, static: bool, complexity: int):
        import mediapipe as mp
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=static, model_complexity=complexity,
            min_detection_confidence=0.5, min_tracking_confidence=0.5, smooth_landmarks=not static,
        )

    def process(self, rgb, ts_ms=0):
        res = self.pose.process(rgb)
        if not res.pose_landmarks:
            return None
        return [(p.x, p.y, p.visibility) for p in res.pose_landmarks.landmark]

    def close(self):
        try:
            self.pose.close()
        except Exception:
            pass


class _TasksBackend:
    """Repli pour les versions récentes de mediapipe (API « tasks », modèle téléchargé une fois)."""

    def __init__(self, static: bool, complexity: int):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self.mp = mp
        self.static = static
        path = self._model_path("pose_landmarker_heavy" if static else "pose_landmarker_full")
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.IMAGE if static else vision.RunningMode.VIDEO,
            num_poses=1, min_pose_detection_confidence=0.5,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(opts)

    @staticmethod
    def _model_path(name):
        folder = DATA_DIR / "models"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name}.task"
        if not path.exists():
            try:
                urllib.request.urlretrieve(_MODEL_URL.format(name=name), str(path) + ".part")
                os.replace(str(path) + ".part", path)
            except Exception as exc:
                raise RuntimeError(
                    "Impossible de télécharger le modèle de détection de pose (connexion Internet requise au premier lancement). "
                    "Alternative : installez une version de mediapipe avec l'API classique, par exemple « pip install mediapipe==0.10.14 »."
                ) from exc
        return path

    def process(self, rgb, ts_ms=0):
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self.landmarker.detect(img) if self.static else self.landmarker.detect_for_video(img, int(ts_ms))
        if not res.pose_landmarks:
            return None
        return [(p.x, p.y, getattr(p, "visibility", 1.0) or 0.0) for p in res.pose_landmarks[0]]

    def close(self):
        try:
            self.landmarker.close()
        except Exception:
            pass


def _make_backend(mode: str):
    """mode : 'image' ou 'video'."""
    import mediapipe as mp
    static = mode == "image"
    if hasattr(mp, "solutions"):
        return _LegacyBackend(static, 2 if static else 1)
    return _TasksBackend(static, 2 if static else 1)


def detect_image(image_bytes: bytes, max_side: int = 1600):
    """Décode l'image, la redimensionne et détecte les 33 repères. Retourne None si rien n'est détecté."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    h, w = bgr.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    with _LOCK:
        if _STATIC["backend"] is None:
            _STATIC["backend"] = _make_backend("image")
        lms = _STATIC["backend"].process(rgb)
    if lms is None:
        return None
    return {"image": rgb, "landmarks": lms}


# ------------------------------------------------------------------------------
#  GÉOMÉTRIE ET MÉTRIQUES
# ------------------------------------------------------------------------------
def side_points(lms, side, w, h):
    pre = "RIGHT" if side == "Droit" else "LEFT"
    pts, vis = {}, {}
    for n in NAMES:
        x, y, v = lms[IDX[f"{pre}_{n}"]][:3]
        pts[n.lower()] = (float(x) * w, float(y) * h)
        vis[n.lower()] = float(v)
    return pts, vis


def mean_visibility(lms, side):
    pre = "RIGHT" if side == "Droit" else "LEFT"
    return float(np.mean([lms[IDX[f"{pre}_{n}"]][2] for n in NAMES]))


def auto_side(lms):
    return "Droit" if mean_visibility(lms, "Droit") >= mean_visibility(lms, "Gauche") else "Gauche"


def is_facing_right(lms, side):
    pre = "RIGHT" if side == "Droit" else "LEFT"
    return lms[IDX["NOSE"]][0] > lms[IDX[f"{pre}_HIP"]][0]


def angle_3pts(a, b, c):
    ba = np.array(a, dtype=float) - np.array(b, dtype=float)
    bc = np.array(c, dtype=float) - np.array(b, dtype=float)
    den = np.linalg.norm(ba) * np.linalg.norm(bc)
    if den == 0:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / den, -1, 1))))


def torso_inclination(shoulder, hip):
    dx = abs(shoulder[0] - hip[0])
    dy = abs(hip[1] - shoulder[1])
    return float(np.degrees(np.arctan2(dy, dx)))


def compute_metrics(pts):
    return {
        "knee": angle_3pts(pts["hip"], pts["knee"], pts["ankle"]),
        "torso": torso_inclination(pts["shoulder"], pts["hip"]),
        "hip": angle_3pts(pts["shoulder"], pts["hip"], pts["knee"]),
        "shoulder": angle_3pts(pts["hip"], pts["shoulder"], pts["elbow"]),
        "elbow": angle_3pts(pts["shoulder"], pts["elbow"], pts["wrist"]),
        "ankle": angle_3pts(pts["knee"], pts["ankle"], pts["foot_index"]),
    }


def evaluate(value, lo, hi, tol):
    dist = max(lo - value, value - hi, 0.0)
    direction = "low" if value < lo else ("high" if value > hi else "in")
    score = max(0.0, 100.0 * (1 - dist / (2 * tol)))
    status = "ok" if dist == 0 else ("warn" if dist <= tol * 0.6 else "bad")
    return {"status": status, "score": score, "dist": dist, "dir": direction}


def evaluate_all(m, ranges):
    return {k: evaluate(m[k], ranges[k][0], ranges[k][1], META[k]["tol"]) for k in ORDER}


def global_score(ev):
    return sum(META[k]["w"] * ev[k]["score"] for k in ORDER) / sum(META[k]["w"] for k in ORDER)


def verdict_for(score):
    if score >= 85:
        return "Position excellente", "Votre réglage est très proche de l'optimum. Quelques micro-ajustements suffisent."
    if score >= 70:
        return "Bonne position", "Une base solide : traitez les points signalés pour gagner en confort et en rendement."
    if score >= 50:
        return "À optimiser", "Plusieurs paramètres s'écartent des plages cibles. Suivez le plan d'action."
    return "Réglages prioritaires", "Des écarts importants ont été détectés : corrigez-les en premier, un par un."


def leg_tilt_deg(pts):
    ax, ay = pts["ankle"]
    hx, hy = pts["hip"]
    return math.degrees(math.atan2(abs(ax - hx), max(1.0, ay - hy)))


def assess_quality(lms, vis, pts, w, h, image=None):
    """Évalue la qualité de la prise de vue : visibilité, profil, cadrage, taille du sujet, lumière."""
    notes = []
    score = float(np.mean(list(vis.values()))) * 100
    torso_len = max(1.0, math.dist(pts["shoulder"], pts["hip"]))
    ratio = abs(lms[IDX["LEFT_SHOULDER"]][0] - lms[IDX["RIGHT_SHOULDER"]][0]) * w / torso_len
    if ratio > 0.30:
        score -= min(25, (ratio - 0.30) * 80)
        notes.append(("warn", "La vue semble légèrement de trois-quarts : les deux épaules sont visibles. Placez l'appareil bien à 90° du vélo."))
    low = [k for k, v in vis.items() if v < 0.5]
    if low:
        score -= 8
        notes.append(("warn", "Repères peu visibles (" + ", ".join(low) + ") : vérifiez l'éclairage, les vêtements contrastés et le cadrage."))
    tilt = leg_tilt_deg(pts)
    if tilt > 32:
        score -= 10
        notes.append(("bad", "La jambe semble très inclinée : la manivelle n'est probablement pas au point mort bas (6 h)."))
    mx, my = 0.02 * w, 0.02 * h
    cut = [k for k, (x, y) in pts.items() if x < mx or x > w - mx or y < my or y > h - my]
    if cut:
        score -= 8
        notes.append(("warn", "Une partie du corps touche le bord de l'image : reculez l'appareil ou cadrez plus large."))
    ys = [l[1] for l in lms if l[2] > 0.5]
    if ys and (max(ys) - min(ys)) < 0.45:
        score -= 5
        notes.append(("warn", "Le cycliste occupe moins de la moitié de la hauteur de l'image : rapprochez-vous pour gagner en précision."))
    if image is not None:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        mean, std = float(gray.mean()), float(gray.std())
        if mean < 60:
            score -= 5
            notes.append(("warn", "Image sombre : ajoutez de la lumière pour améliorer la détection."))
        elif mean > 200:
            score -= 5
            notes.append(("warn", "Image très claire / surexposée : évitez le contre-jour."))
        elif std < 25:
            score -= 4
            notes.append(("warn", "Contraste faible : portez des vêtements ajustés qui contrastent avec le fond."))
    if not notes:
        notes.append(("ok", "Prise de vue exploitable : profil net, repères bien détectés."))
    return max(0.0, min(100.0, score)), notes, tilt


# ------------------------------------------------------------------------------
#  CALIBRATION ET MODÈLE DE JAMBE
# ------------------------------------------------------------------------------
def leg_segments_mm(height_cm, measured=None):
    """Cuisse et jambe en mm : modèle de Drillis & Contini, ou valeurs mesurées si plausibles."""
    a0, b0 = 0.245 * height_cm * 10, 0.246 * height_cm * 10
    if measured:
        a, b = measured
        if 0.75 * a0 <= a <= 1.25 * a0 and 0.75 * b0 <= b <= 1.25 * b0:
            return a, b
    return a0, b0


def auto_scale(pts, height_cm):
    """Échelle (pixels par mm) estimée à partir de la taille et des segments cuisse / jambe."""
    s1 = math.dist(pts["hip"], pts["knee"]) / (0.245 * height_cm * 10)
    s2 = math.dist(pts["knee"], pts["ankle"]) / (0.246 * height_cm * 10)
    return (s1 + s2) / 2


def manual_scale(p1, p2, length_cm):
    return math.dist(p1, p2) / max(1e-6, length_cm * 10)


def segments_mm(pts, scale):
    d = lambda a, b: math.dist(pts[a], pts[b]) / scale
    return {
        "Cuisse": d("hip", "knee"), "Jambe": d("knee", "ankle"), "Tronc": d("shoulder", "hip"),
        "Bras": d("shoulder", "elbow"), "Avant-bras": d("elbow", "wrist"),
    }


def hip_ankle_dist(knee_deg, seg):
    a, b = seg
    return math.sqrt(max(0.0, a * a + b * b - 2 * a * b * math.cos(math.radians(knee_deg))))


def saddle_delta_mm(knee_deg, target_deg, seg):
    return hip_ankle_dist(target_deg, seg) - hip_ankle_dist(knee_deg, seg)


def knee_after_delta(knee_deg, delta_mm, seg):
    a, b = seg
    d1 = hip_ankle_dist(knee_deg, seg) + delta_mm
    c = (a * a + b * b - d1 * d1) / (2 * a * b)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def torso_after_bar_delta(torso_deg, delta_mm, height_cm):
    T = 0.288 * height_cm * 10
    sv = math.sin(math.radians(torso_deg)) + delta_mm / T
    return math.degrees(math.asin(max(0.0, min(1.0, sv))))


def crank_length_suggestion(inseam_cm):
    target = inseam_cm * 10 * 0.216
    options = [160, 165, 167.5, 170, 172.5, 175, 177.5, 180]
    return min(options, key=lambda o: abs(o - target)), target


def bar_width_suggestion(shoulder_cm):
    options = [36, 38, 40, 42, 44, 46]
    return min(options, key=lambda o: abs(o - shoulder_cm))


# ------------------------------------------------------------------------------
#  DESSIN SUR L'IMAGE
# ------------------------------------------------------------------------------
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def put_label(img, text, org, color, s):
    font = cv2.FONT_HERSHEY_SIMPLEX
    th_ = max(1, int(round(s * 2)))
    (tw, th), bl = cv2.getTextSize(text, font, s, th_)
    x, y = int(org[0]), int(org[1])
    x = max(6, min(img.shape[1] - tw - 24, x))
    y = max(th + 8, min(img.shape[0] - 8, y))
    cv2.rectangle(img, (x - 6, y - th - 6), (x + tw + 16, y + bl + 4), (7, 11, 22), -1)
    cv2.rectangle(img, (x - 6, y - th - 6), (x + tw + 16, y + bl + 4), color, 1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, s, (240, 245, 255), th_, cv2.LINE_AA)
    cv2.circle(img, (x + tw + 7, y - th + 1), max(2, int(s * 4)), color, 1, cv2.LINE_AA)


def draw_grid(img):
    h, w = img.shape[:2]
    c = (255, 255, 255)
    over = img.copy()
    for i in (1, 2):
        cv2.line(over, (w * i // 3, 0), (w * i // 3, h), c, 1, cv2.LINE_AA)
        cv2.line(over, (0, h * i // 3), (w, h * i // 3), c, 1, cv2.LINE_AA)
    cv2.circle(over, (w // 2, h // 2), max(6, w // 120), c, 1, cv2.LINE_AA)
    return cv2.addWeighted(over, 0.45, img, 0.55, 0)


def annotate(rgb, pts, m, ev, grid=False):
    """Squelette cycliste, arcs d'angle et étiquettes colorées par statut."""
    h, w = rgb.shape[:2]
    s = w / 1000.0
    base = rgb.copy()
    overlay = rgb.copy()
    col = {k: hex_rgb(STATUS[ev[k]["status"]][0]) for k in ORDER}
    P = {k: (int(v[0]), int(v[1])) for k, v in pts.items()}
    thick = max(3, int(5 * s))
    ref = (120, 140, 170)
    cv2.line(base, (P["hip"][0] - int(200 * s), P["hip"][1]), (P["hip"][0] + int(200 * s), P["hip"][1]), ref, max(1, int(2 * s)), cv2.LINE_AA)
    cv2.line(base, (P["ankle"][0], P["ankle"][1] - int(330 * s)), (P["ankle"][0], P["ankle"][1] + int(30 * s)), ref, max(1, int(2 * s)), cv2.LINE_AA)
    r = max(18, int(46 * s))
    triples = {
        "knee": (P["hip"], P["knee"], P["ankle"]),
        "hip": (P["shoulder"], P["hip"], P["knee"]),
        "elbow": (P["shoulder"], P["elbow"], P["wrist"]),
        "shoulder": (P["hip"], P["shoulder"], P["elbow"]),
        "ankle": (P["knee"], P["ankle"], P["foot_index"]),
    }
    arcs = {}
    for k, (a, b, c) in triples.items():
        a1 = math.degrees(math.atan2(a[1] - b[1], a[0] - b[0]))
        a2 = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]))
        diff = (a2 - a1 + 540) % 360 - 180
        st_, en_ = (a1, a1 + diff) if diff >= 0 else (a1 + diff, a1)
        arcs[k] = (st_, en_)
        cv2.ellipse(overlay, b, (r, r), 0, st_, en_, col[k], -1, cv2.LINE_AA)
    base = cv2.addWeighted(overlay, 0.35, base, 0.65, 0)
    for k, (a, b, c) in triples.items():
        cv2.ellipse(base, b, (r, r), 0, arcs[k][0], arcs[k][1], col[k], max(2, int(3 * s)), cv2.LINE_AA)
    for a, b, k in (("hip", "knee", "knee"), ("knee", "ankle", "knee"), ("shoulder", "hip", "torso"),
                    ("shoulder", "elbow", "elbow"), ("elbow", "wrist", "elbow")):
        cv2.line(base, P[a], P[b], (7, 11, 22), thick + 4, cv2.LINE_AA)
        cv2.line(base, P[a], P[b], col[k], thick, cv2.LINE_AA)
    for a, b in (("ankle", "heel"), ("heel", "foot_index"), ("ankle", "foot_index")):
        cv2.line(base, P[a], P[b], (190, 205, 225), max(2, int(3 * s)), cv2.LINE_AA)
    for p in P.values():
        cv2.circle(base, p, max(6, int(9 * s)), (7, 11, 22), -1, cv2.LINE_AA)
        cv2.circle(base, p, max(4, int(6 * s)), (245, 248, 255), -1, cv2.LINE_AA)
    for k, (a, b, c) in triples.items():
        u1 = np.array(a, float) - np.array(b, float)
        u2 = np.array(c, float) - np.array(b, float)
        u1 /= (np.linalg.norm(u1) or 1)
        u2 /= (np.linalg.norm(u2) or 1)
        bis = u1 + u2
        if np.linalg.norm(bis) < 1e-3:
            bis = np.array([-u1[1], u1[0]])
        bis /= (np.linalg.norm(bis) or 1)
        pos = np.array(b, float) + bis * (r + 34 * s) + np.array([-24 * s, 8 * s])
        put_label(base, f"{m[k]:.0f}", pos, col[k], max(0.6, 0.85 * s))
    mid = ((P["shoulder"][0] + P["hip"][0]) // 2, (P["shoulder"][1] + P["hip"][1]) // 2)
    off = -90 * s if P["shoulder"][0] >= P["hip"][0] else 40 * s
    put_label(base, f"tronc {m['torso']:.0f}", (mid[0] + off, mid[1]), col["torso"], max(0.6, 0.8 * s))
    if grid:
        base = draw_grid(base)
    return base


def draw_calibration(rgb, p1, p2, label):
    out = rgb.copy()
    s = out.shape[1] / 1000.0
    a, b = (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1]))
    cv2.line(out, a, b, (251, 191, 36), max(2, int(4 * s)), cv2.LINE_AA)
    for p in (a, b):
        cv2.circle(out, p, max(5, int(9 * s)), (251, 191, 36), -1, cv2.LINE_AA)
    put_label(out, label, ((a[0] + b[0]) / 2 + 10, (a[1] + b[1]) / 2), (251, 191, 36), max(0.6, 0.8 * s))
    return out


# ------------------------------------------------------------------------------
#  RECOMMANDATIONS
# ------------------------------------------------------------------------------
def build_recommendations(m, ev, ranges, ctx):
    """ctx : height (cm), seg (cuisse, jambe en mm), discipline."""
    seg = ctx["seg"]
    H_ = ctx["height"]
    tt = ctx.get("discipline", "").startswith("Triathlon")
    recs = []

    def add(key, status, title, diag, actions=None):
        recs.append(dict(key=key, status=status, title=title, diag=diag, actions=actions or [], why=METRIC_WHY[key]))

    lo, hi = ranges["knee"]
    k = ev["knee"]
    if k["dir"] == "low":
        mm = round(saddle_delta_mm(m["knee"], lo + 2, seg))
        add("knee", k["status"], "Selle trop basse",
            f"Genou à <b>{m['knee']:.1f}°</b> au point mort bas (cible {lo}–{hi}°) : la flexion résiduelle est trop importante, "
            "ce qui réduit l'efficacité de la poussée et charge l'articulation fémoro-patellaire.",
            [f"Monter la selle d'environ <b>{mm} mm</b> (estimation pour une taille de {H_} cm), par paliers de 2 à 3 mm.",
             "Tester une sortie entre chaque ajustement, puis refaire une analyse au point mort bas.",
             "Contrôler ensuite le recul de selle (onglet « Selle & recul »)."])
    elif k["dir"] == "high":
        mm = abs(round(saddle_delta_mm(m["knee"], hi - 2, seg)))
        add("knee", k["status"], "Selle trop haute",
            f"Genou à <b>{m['knee']:.1f}°</b> (cible {lo}–{hi}°) : l'extension est excessive, avec risque de bascule du bassin, "
            "de tension des ischio-jambiers et de tendinopathie du tendon d'Achille.",
            [f"Descendre la selle d'environ <b>{mm} mm</b>, par paliers de 2 à 3 mm.",
             "Vérifier que le bassin ne se balance plus latéralement à vitesse stabilisée.",
             "Contrôler la position des cales (onglet « Cales & matériel »)."])
    else:
        add("knee", "ok", "Hauteur de selle optimale",
            f"Genou à <b>{m['knee']:.1f}°</b>, dans la plage cible {lo}–{hi}° (≈ {180 - m['knee']:.0f}° de flexion résiduelle).")

    lo, hi = ranges["ankle"]
    k = ev["ankle"]
    if k["dir"] == "high":
        add("ankle", k["status"], "Pointe de pied très tendue",
            f"Angle de cheville de <b>{m['ankle']:.0f}°</b> (cible {lo}–{hi}°) : forte flexion plantaire, souvent associée à une selle haute ou à des cales trop avancées.",
            ["Recouper avec l'angle du genou avant toute modification.",
             "Vérifier que l'articulation du gros orteil est à l'aplomb de l'axe de pédale (cales).",
             "Mesure indicative : la précision de la cheville dépend du cadrage."])
    elif k["dir"] == "low":
        add("ankle", k["status"], "Talon très bas",
            f"Angle de cheville de <b>{m['ankle']:.0f}°</b> (cible {lo}–{hi}°) : le talon plonge, ce qui peut indiquer une selle basse ou des cales trop reculées.",
            ["Recouper avec l'angle du genou.", "Avancer légèrement les cales de 2–3 mm et réévaluer.",
             "Mesure indicative : prise de vue de profil strict nécessaire."])
    else:
        add("ankle", "ok", "Cheville cohérente", f"Angle de <b>{m['ankle']:.0f}°</b> dans la plage attendue ({lo}–{hi}°).")

    lo, hi = ranges["torso"]
    k = ev["torso"]
    if k["dir"] == "low":
        add("torso", k["status"], "Posture plus basse que la cible",
            f"Tronc à <b>{m['torso']:.0f}°</b> de l'horizontale (cible {lo}–{hi}°). Position très aérodynamique, mais exigeante pour les lombaires, la nuque et les mains.",
            ["Relever le cintre de 10 mm (entretoises) puis réévaluer.", "Option : potence plus courte ou à angle plus relevé.",
             "Travailler la mobilité des ischio-jambiers et la gaine abdominale pour tenir la position."])
    elif k["dir"] == "high":
        extra = "Sur vélo de contre-la-montre, cette posture est trop relevée pour exploiter les prolongateurs. " if tt else ""
        add("torso", k["status"], "Posture plus relevée que la cible",
            f"{extra}Tronc à <b>{m['torso']:.0f}°</b> (cible {lo}–{hi}°). Confort élevé, mais prise au vent importante et appui accru sur la selle.",
            ["Si l'objectif est la performance : retirer une entretoise de 5 à 10 mm progressivement.",
             "Option : potence plus longue (+10 mm) pour allonger le buste.",
             "Progresser par paliers sur 3 à 4 semaines pour laisser le corps s'adapter."])
    else:
        add("torso", "ok", "Inclinaison du tronc validée", f"Tronc à <b>{m['torso']:.0f}°</b>, cohérent avec la plage {lo}–{hi}° pour votre profil.")

    lo, hi = ranges["hip"]
    k = ev["hip"]
    if k["dir"] == "low":
        add("hip", k["status"], "Hanche trop fermée",
            f"Angle tronc-cuisse de <b>{m['hip']:.0f}°</b> (cible {lo}–{hi}°) : l'abdomen est comprimé, l'amplitude respiratoire et la liberté du bassin sont limitées.",
            ["Relever le cintre ou raccourcir légèrement la potence.", "Vérifier l'inclinaison de la selle (nez non relevé) et un recul suffisant.",
             "Assouplir les fléchisseurs de hanche (psoas, droit fémoral)."])
    elif k["dir"] == "high":
        add("hip", k["status"], "Hanche très ouverte",
            f"Angle de <b>{m['hip']:.0f}°</b> (cible {lo}–{hi}°) : posture très verticale, favorable au confort mais peu aérodynamique.",
            ["Abaisser progressivement le cintre si vous recherchez de la performance.", "Sinon, conserver ce réglage pour l'endurance longue distance."])
    else:
        add("hip", "ok", "Ouverture de hanche correcte", f"Angle de <b>{m['hip']:.0f}°</b> dans la cible {lo}–{hi}° : bonne liberté de mouvement.")

    lo, hi = ranges["shoulder"]
    k = ev["shoulder"]
    if k["dir"] == "high":
        add("shoulder", k["status"], "Allonge trop importante",
            f"Angle épaule de <b>{m['shoulder']:.0f}°</b> (cible {lo}–{hi}°) : les bras partent trop loin vers l'avant, transférant du poids sur les mains et les épaules.",
            ["Raccourcir la potence de 10 mm et réévaluer.", "Vérifier le recul de selle : une selle trop reculée allonge artificiellement le cockpit."])
    elif k["dir"] == "low":
        add("shoulder", k["status"], "Allonge trop courte",
            f"Angle épaule de <b>{m['shoulder']:.0f}°</b> (cible {lo}–{hi}°) : le cockpit est compact, les épaules sont repliées sur le buste.",
            ["Allonger la potence de 10 mm.", "Vérifier que les genoux ne touchent pas les bras en danseuse."])
    else:
        add("shoulder", "ok", "Allonge adaptée", f"Angle épaule de <b>{m['shoulder']:.0f}°</b> dans la cible {lo}–{hi}°.")

    lo, hi = ranges["elbow"]
    k = ev["elbow"]
    if k["dir"] == "high":
        if tt:
            add("elbow", k["status"], "Appuis trop éloignés",
                f"Angle du coude de <b>{m['elbow']:.0f}°</b> (cible {lo}–{hi}°) : les bras sont trop tendus sur les prolongateurs.",
                ["Raccourcir l'allonge des prolongateurs ou avancer les coudes sur les appuis.", "Vérifier la hauteur des appuis (stack)."])
        else:
            add("elbow", k["status"], "Bras quasi tendus",
                f"Angle du coude de <b>{m['elbow']:.0f}°</b> (cible {lo}–{hi}°) : les vibrations remontent directement aux épaules et aux poignets.",
                ["Raccourcir la potence ou relever le cintre.", "Garder les coudes déverrouillés en roulant."])
    elif k["dir"] == "low":
        add("elbow", k["status"], "Coudes très fléchis",
            f"Angle du coude de <b>{m['elbow']:.0f}°</b> (cible {lo}–{hi}°) : cockpit probablement trop court ou trop bas pour votre souplesse.",
            ["Allonger la potence de 10 mm ou relever légèrement le cintre."])
    else:
        add("elbow", "ok", "Flexion de coude idéale", f"Angle de <b>{m['elbow']:.0f}°</b> dans la cible {lo}–{hi}° : bonne absorption des chocs.")
    return recs


def pain_analysis(complaints, ev):
    out = []
    for c in complaints:
        hits = [(k, d) for k, d in COMPLAINTS[c] if ev[k]["dir"] == d]
        if hits:
            names = ", ".join(META[k]["label"].lower() for k, _ in hits)
            out.append(("bad", c, f"Corrélation détectée avec : <b>{names}</b>. La mesure est cohérente avec ce symptôme, c'est la première piste à traiter."))
        else:
            out.append(("warn", c, "Aucune anomalie directement liée sur cette analyse. Causes possibles non mesurables ici : "
                                   "inclinaison de selle, largeur de cintre, position des cales, longueur de manivelle ou matériel."))
    return out


# ------------------------------------------------------------------------------
#  ANALYSE VIDÉO (pédalage dynamique)
# ------------------------------------------------------------------------------
def _interp_nan(a):
    a = np.asarray(a, float)
    idx = np.arange(len(a))
    good = ~np.isnan(a)
    if good.sum() < 2:
        return a
    return np.interp(idx, idx[good], a[good])


def _smooth(a, win=3):
    a2 = _interp_nan(a)
    if len(a2) < win or np.isnan(a2).any():
        return a2
    pad = win // 2
    padded = np.pad(a2, (pad, pad), mode="edge")
    return np.convolve(padded, np.ones(win) / win, mode="valid")


def find_peaks(x, d, min_prom):
    x = np.asarray(x, float)
    n = len(x)
    out = []
    for i in range(d, n - d):
        seg = x[max(0, i - d): min(n, i + d + 1)]
        if x[i] == np.max(seg) and x[i] - np.min(seg) >= min_prom:
            if out and i - out[-1] <= d:
                if x[i] > x[out[-1]]:
                    out[-1] = i
                continue
            out.append(i)
    return out


def analyze_video(path, side="Auto", max_seconds=15.0, target_fps=20.0, width=640, progress=None):
    """Analyse un clip de pédalage : angles par image, cycles, cadence, valeurs moyennes au point mort bas."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"error": "Impossible d'ouvrir la vidéo. Essayez un fichier MP4 ou MOV."}
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, int(round(fps / target_fps)))
    fps_eff = fps / step
    expected = max(1, int(min(total / step if total else max_seconds * fps_eff, max_seconds * fps_eff)))
    backend = _make_backend("video")
    jpegs, rows, times = [], [], []
    i = 0
    w = h = 0
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            t = i / fps
            if t > max_seconds:
                break
            if i % step == 0:
                hh, ww = bgr.shape[:2]
                if ww > width:
                    bgr = cv2.resize(bgr, (width, int(hh * width / ww)), interpolation=cv2.INTER_AREA)
                h, w = bgr.shape[:2]
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                lms = backend.process(rgb, ts_ms=int(t * 1000))
                rows.append(np.array(lms, dtype=float) if lms is not None else np.full((33, 3), np.nan))
                okj, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
                jpegs.append(buf.tobytes() if okj else b"")
                times.append(t)
                if progress:
                    progress(min(0.99, len(rows) / expected), f"Image {len(rows)} / ~{expected}")
            i += 1
    finally:
        cap.release()
        backend.close()
    n = len(rows)
    arr = np.array(rows) if n else np.zeros((0, 33, 3))
    valid = ~np.isnan(arr[:, 0, 0]) if n else np.array([], bool)
    if n < 10 or valid.sum() < 10:
        return {"error": "Le cycliste n'a pas été détecté sur assez d'images. Vérifiez le cadrage, la lumière et filmez de profil."}
    if side == "Auto":
        vr = np.nanmean([mean_visibility(arr[j], "Droit") for j in np.where(valid)[0]])
        vl = np.nanmean([mean_visibility(arr[j], "Gauche") for j in np.where(valid)[0]])
        side = "Droit" if vr >= vl else "Gauche"

    keys = ["knee", "hip", "torso", "shoulder", "elbow", "ankle"]
    raw = {k: np.full(n, np.nan) for k in keys}
    for j in range(n):
        if not valid[j]:
            continue
        pts, vis = side_points(arr[j], side, w, h)
        if min(vis["hip"], vis["knee"], vis["ankle"]) < 0.3:
            continue
        mm = compute_metrics(pts)
        for k in keys:
            raw[k][j] = mm[k]
    sm = {k: _smooth(raw[k]) for k in keys}
    knee = sm["knee"]
    if np.isnan(knee).any():
        return {"error": "Les repères de la jambe sont trop souvent masqués : cadrez la jambe entière, de profil."}
    rom_series = float(np.percentile(knee, 95) - np.percentile(knee, 5))
    if rom_series < 15:
        return {"error": "Aucun pédalage détecté (amplitude du genou trop faible). Filmez au moins 5 secondes de pédalage régulier."}
    d = max(2, int(0.2 * fps_eff))
    prom = 0.4 * rom_series
    bdc = find_peaks(knee, d, prom)
    top = find_peaks(-knee, d, prom)
    if len(bdc) < 2:
        return {"error": "Moins de deux tours de manivelle détectés. Filmez au moins 5 à 10 secondes de pédalage régulier."}
    tarr = np.array(times)
    cadence = float(60.0 / np.median(np.diff(tarr[bdc])))
    m = {k: float(np.nanmean(sm[k][bdc])) for k in keys}
    bdc_vals = knee[bdc]
    best = int(bdc[int(np.argmin(np.abs(bdc_vals - bdc_vals.mean())))])
    bgr_best = cv2.imdecode(np.frombuffer(jpegs[best], np.uint8), cv2.IMREAD_COLOR)
    return {
        "side": side, "m": m, "cadence": cadence, "n": n, "fps": fps_eff, "width": w, "height": h,
        "times": tarr.tolist(), "knee": knee.tolist(), "hip_series": sm["hip"].tolist(),
        "bdc": [int(x) for x in bdc], "top": [int(x) for x in top],
        "knee_max": float(np.mean(knee[bdc])), "knee_min": float(np.mean(knee[top])) if top else float("nan"),
        "rom": float(np.mean(knee[bdc]) - np.mean(knee[top])) if top else float("nan"),
        "bdc_std": float(np.std(bdc_vals)),
        "hip_min": float(np.mean(sm["hip"][top])) if top else float("nan"),
        "detected_ratio": float(valid.mean()), "best": best,
        "image": cv2.cvtColor(bgr_best, cv2.COLOR_BGR2RGB), "lms_best": arr[best].tolist(),
    }


def pedal_notes(res):
    """Observations sur le cycle de pédalage (statut, titre, texte)."""
    notes = []
    cad = res["cadence"]
    if cad < 60:
        notes.append(("warn", "Cadence basse", f"Cadence estimée à {cad:.0f} tr/min : très faible, ce qui peut surcharger les genoux. Vérifiez que la vidéo est filmée à vitesse normale."))
    elif cad > 120:
        notes.append(("warn", "Cadence élevée", f"Cadence estimée à {cad:.0f} tr/min : à cette vitesse, la précision de l'analyse diminue (images trop espacées)."))
    else:
        notes.append(("ok", "Cadence exploitable", f"Cadence estimée à {cad:.0f} tr/min."))
    std = res["bdc_std"]
    if std > 5:
        notes.append(("bad", "Pédalage irrégulier", f"L'angle du genou au point bas varie de ±{std:.1f}° d'un tour à l'autre : bascule du bassin possible (selle haute ?) ou détection instable."))
    elif std > 3:
        notes.append(("warn", "Légère variabilité", f"Variation de ±{std:.1f}° de l'angle du genou entre les tours. Vérifiez la hauteur de selle et la stabilité du bassin."))
    else:
        notes.append(("ok", "Pédalage régulier", f"Variation de seulement ±{std:.1f}° entre les tours."))
    if not math.isnan(res["hip_min"]) and res["hip_min"] < 55:
        notes.append(("warn", "Hanche très fermée au point haut", f"L'angle de hanche descend à {res['hip_min']:.0f}° au sommet de la course : cintre bas ou selle haute possible."))
    if not math.isnan(res["rom"]):
        notes.append(("ok", "Amplitude du genou", f"Le genou passe de {res['knee_min']:.0f}° (point haut) à {res['knee_max']:.0f}° (point bas), soit {res['rom']:.0f}° d'amplitude."))
    return notes


# ------------------------------------------------------------------------------
#  VUE DE FACE (symétrie)
# ------------------------------------------------------------------------------
def _tilt(a, b):
    ang = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])))
    return min(ang, 180 - ang)


def analyze_frontal(rgb, lms):
    """Analyse d'une photo de face ou de dos : bassin, épaules, alignement des genoux, inclinaison du buste."""
    h, w = rgb.shape[:2]
    P = lambda n: np.array([lms[IDX[n]][0] * w, lms[IDX[n]][1] * h])
    lsh, rsh, lhip, rhip = P("LEFT_SHOULDER"), P("RIGHT_SHOULDER"), P("LEFT_HIP"), P("RIGHT_HIP")
    lk, rk, la, ra = P("LEFT_KNEE"), P("RIGHT_KNEE"), P("LEFT_ANKLE"), P("RIGHT_ANKLE")
    mid_x = (lhip[0] + rhip[0]) / 2

    def knee_dev(hip, knee, ankle):
        t = (knee[1] - hip[1]) / (ankle[1] - hip[1]) if abs(ankle[1] - hip[1]) > 1e-6 else 0.5
        xline = hip[0] + t * (ankle[0] - hip[0])
        sign = 1.0 if (mid_x - hip[0]) >= 0 else -1.0
        return (knee[0] - xline) * sign / max(1.0, np.linalg.norm(ankle - hip)) * 100.0

    vl, vr = knee_dev(lhip, lk, la), knee_dev(rhip, rk, ra)
    pelvis = _tilt(lhip, rhip)
    shoulders = _tilt(lsh, rsh)
    mid_sh, mid_hip = (lsh + rsh) / 2, (lhip + rhip) / 2
    lean = math.degrees(math.atan2(abs(mid_sh[0] - mid_hip[0]), max(1.0, abs(mid_hip[1] - mid_sh[1]))))
    low_hip = "gauche" if lhip[1] > rhip[1] else "droite"
    low_sh = "gauche" if lsh[1] > rsh[1] else "droite"

    def st(v, ok, warn):
        a = abs(v)
        return "ok" if a <= ok else ("warn" if a <= warn else "bad")

    items = [
        dict(key="pelvis", label="Inclinaison du bassin", value=pelvis, unit="°", status=st(pelvis, 2, 4),
             text=f"Le bassin est incliné de {pelvis:.1f}° (côté {low_hip} plus bas). Au-delà de 2–3°, pensez à une selle trop haute, une différence de longueur de jambe ou une cale à ajuster."),
        dict(key="shoulders", label="Inclinaison des épaules", value=shoulders, unit="°", status=st(shoulders, 3, 5),
             text=f"Épaules inclinées de {shoulders:.1f}° (côté {low_sh} plus bas) : vérifiez l'appui sur le guidon et la symétrie de la position."),
        dict(key="lean", label="Inclinaison latérale du buste", value=lean, unit="°", status=st(lean, 3, 6),
             text=f"Le buste penche de {lean:.1f}° par rapport à la verticale du bassin : cherchez un appui inégal sur la selle ou le cintre."),
        dict(key="knee_l", label="Genou gauche (écart latéral)", value=vl, unit="%", status=st(vl, 4, 8),
             text=("Le genou gauche part vers l'intérieur (valgus)" if vl > 0 else "Le genou gauche part vers l'extérieur (varus)") +
                  f" de {abs(vl):.1f} % de la longueur de jambe. Contrôlez la rotation des cales, l'écartement des pédales (Q-factor) et la hauteur de selle."),
        dict(key="knee_r", label="Genou droit (écart latéral)", value=vr, unit="%", status=st(vr, 4, 8),
             text=("Le genou droit part vers l'intérieur (valgus)" if vr > 0 else "Le genou droit part vers l'extérieur (varus)") +
                  f" de {abs(vr):.1f} % de la longueur de jambe. Contrôlez la rotation des cales, l'écartement des pédales (Q-factor) et la hauteur de selle."),
    ]
    sym = abs(vl - vr)
    items.append(dict(key="sym", label="Asymétrie des genoux", value=sym, unit="%", status=st(sym, 4, 8),
                      text=f"Écart de {sym:.1f} points entre les deux genoux : une asymétrie importante peut venir d'une jambe plus longue ou d'une mobilité différente."))
    colors = {it["key"]: hex_rgb(STATUS[it["status"]][0]) for it in items}
    out = rgb.copy()
    s = w / 1000.0
    th = max(3, int(5 * s))
    I = lambda p: (int(p[0]), int(p[1]))
    cv2.line(out, I(mid_sh), I(mid_hip), (120, 140, 170), max(1, int(2 * s)), cv2.LINE_AA)
    cv2.line(out, (int(mid_x), 0), (int(mid_x), h), (120, 140, 170), 1, cv2.LINE_AA)
    cv2.line(out, I(lhip), I(rhip), colors["pelvis"], th, cv2.LINE_AA)
    cv2.line(out, I(lsh), I(rsh), colors["shoulders"], th, cv2.LINE_AA)
    for hip, knee, ankle, key in ((lhip, lk, la, "knee_l"), (rhip, rk, ra, "knee_r")):
        cv2.line(out, I(hip), I(knee), colors[key], th, cv2.LINE_AA)
        cv2.line(out, I(knee), I(ankle), colors[key], th, cv2.LINE_AA)
        cv2.line(out, I(hip), I(ankle), (190, 205, 225), max(1, int(2 * s)), cv2.LINE_AA)
    for p in (lsh, rsh, lhip, rhip, lk, rk, la, ra):
        cv2.circle(out, I(p), max(5, int(8 * s)), (245, 248, 255), -1, cv2.LINE_AA)
    put_label(out, f"bassin {pelvis:.1f}", (lhip[0] + 12, lhip[1] - 12), colors["pelvis"], max(0.55, 0.7 * s))
    for it in items:
        it["value"] = float(it["value"])
    return {"items": items, "image": out}


# ------------------------------------------------------------------------------
#  RECUL DE SELLE (KOPS, manivelle à 3 h)
# ------------------------------------------------------------------------------
def kops_analysis(lms, side, w, h, scale):
    """Décalage horizontal (mm) entre le genou et l'axe de pédale estimé. Positif = genou en avant."""
    pts, vis = side_points(lms, side, w, h)
    facing = is_facing_right(lms, side)
    heel, toe = np.array(pts["heel"]), np.array(pts["foot_index"])
    spindle = heel + 0.72 * (toe - heel)
    knee = np.array(pts["knee"])
    sign = 1.0 if facing else -1.0
    offset = (knee[0] - spindle[0]) * sign / scale
    knee_angle = angle_3pts(pts["hip"], pts["knee"], pts["ankle"])
    crank_ok = 80 <= knee_angle <= 125
    status = "ok" if abs(offset) <= 15 else ("warn" if abs(offset) <= 30 else "bad")
    return {"offset_mm": float(offset), "status": status, "knee_angle": knee_angle, "crank_ok": crank_ok,
            "spindle": tuple(spindle), "knee": tuple(knee), "facing_right": facing, "pts": pts}


def annotate_kops(rgb, res):
    out = rgb.copy()
    h, w = out.shape[:2]
    s = w / 1000.0
    col = hex_rgb(STATUS[res["status"]][0])
    kx, ky = int(res["knee"][0]), int(res["knee"][1])
    sx, sy = int(res["spindle"][0]), int(res["spindle"][1])
    cv2.line(out, (kx, ky - int(150 * s)), (kx, sy + int(60 * s)), col, max(2, int(3 * s)), cv2.LINE_AA)
    cv2.line(out, (sx, ky - int(150 * s)), (sx, sy + int(60 * s)), (251, 191, 36), max(2, int(3 * s)), cv2.LINE_AA)
    for p in ((kx, ky), (sx, sy)):
        cv2.circle(out, p, max(6, int(10 * s)), (245, 248, 255), -1, cv2.LINE_AA)
    put_label(out, f"genou {res['offset_mm']:+.0f} mm", (kx + 14, ky - int(110 * s)), col, max(0.6, 0.8 * s))
    put_label(out, "axe pedale", (sx + 14, sy + int(40 * s)), (251, 191, 36), max(0.55, 0.7 * s))
    return out


def kops_recommendation(res):
    off = res["offset_mm"]
    if res["status"] == "ok":
        return ("ok", "Recul de selle cohérent", f"Le genou est à {off:+.0f} mm de l'axe de pédale : dans la tolérance habituelle (±15 mm).",
                ["Conservez ce réglage, sauf si vous ressentez des douleurs de genou ou de dos."])
    if off > 0:
        return (res["status"], "Selle probablement trop avancée",
                f"Le genou dépasse l'axe de pédale d'environ {off:.0f} mm : charge accrue sur les quadriceps et l'avant du genou.",
                [f"Reculer la selle d'environ {abs(off):.0f} mm sur ses rails, par paliers de 3 à 5 mm.",
                 "Contrôler la hauteur de selle après chaque déplacement (le recul modifie l'angle du genou).",
                 "Adapter la potence si l'allonge devient trop longue."])
    return (res["status"], "Selle probablement trop reculée",
            f"Le genou est {abs(off):.0f} mm derrière l'axe de pédale : sollicitation accrue des fessiers et ischio-jambiers, allonge plus longue.",
            [f"Avancer la selle d'environ {abs(off):.0f} mm, par paliers de 3 à 5 mm.",
             "Recontrôler la hauteur de selle ensuite.", "Le KOPS est un repère de départ : certains profils (contre-la-montre, grimpeurs) s'en écartent volontairement."])


# ------------------------------------------------------------------------------
#  TRANSFERT DE RÉGLAGES ENTRE DEUX VÉLOS
# ------------------------------------------------------------------------------
TRANSFER_FIELDS = [
    ("saddle_height", "Hauteur de selle (mm)", "Axe du boîtier de pédalier → dessus de selle, le long du tube de selle", 720),
    ("setback", "Recul de selle (mm)", "Pointe de selle derrière la verticale du boîtier de pédalier (négatif si devant)", 60),
    ("reach", "Allonge selle → cintre (mm)", "Pointe de selle → centre du cintre, à l'horizontale", 550),
    ("drop", "Dénivelé selle → cintre (mm)", "Dessus de selle moins dessus du cintre (positif si la selle est plus haute)", 80),
    ("crank", "Longueur de manivelle (mm)", "", 172.5),
    ("bar_width", "Largeur de cintre (mm)", "Centre à centre", 420),
]


def transfer_plan(ref: dict, cur: dict):
    plan = []
    for key, label, _, _ in TRANSFER_FIELDS:
        a, b = ref.get(key), cur.get(key)
        if a is None or b is None:
            continue
        d = float(a) - float(b)
        if abs(d) < 1.5:
            action, status = "Déjà équivalent : rien à changer.", "ok"
        elif key == "saddle_height":
            action, status = (f"Monter la selle de {d:.0f} mm." if d > 0 else f"Descendre la selle de {abs(d):.0f} mm."), "warn"
        elif key == "setback":
            action, status = (f"Reculer la selle de {d:.0f} mm" if d > 0 else f"Avancer la selle de {abs(d):.0f} mm") + " sur ses rails, puis recontrôler la hauteur.", "warn"
        elif key == "reach":
            action, status = (f"Allonger la potence de {d:.0f} mm." if d > 0 else f"Raccourcir la potence de {abs(d):.0f} mm."), "warn"
        elif key == "drop":
            action, status = (f"Abaisser le cintre de {d:.0f} mm (retirer des entretoises ou potence plus inclinée)." if d > 0
                              else f"Relever le cintre de {abs(d):.0f} mm (ajouter des entretoises)."), "warn"
        elif key == "crank":
            action, status = (f"Passer à des manivelles de {a:g} mm, puis {'descendre' if d > 0 else 'monter'} la selle d'environ {abs(d):.0f} mm "
                              "pour compenser."), "warn"
        else:
            action, status = f"Passer à un cintre de {a:g} mm de large.", "warn"
        plan.append(dict(key=key, label=label, ref=a, cur=b, delta=d, action=action, status=status))
    return plan


# ------------------------------------------------------------------------------
#  PERFORMANCE (données de sortie)
# ------------------------------------------------------------------------------
def _find_col(cols, exact, sub):
    for c in cols:
        if c.lower().strip() in exact:
            return c
    for c in cols:
        if any(s in c.lower() for s in sub):
            return c
    return None


def parse_ride_csv(df):
    """Extrait puissance et fréquence cardiaque moyennes d'un export CSV (colonnes détectées automatiquement)."""
    import pandas as pd
    pc = _find_col(df.columns, {"power", "watts", "puissance", "w"}, ["power", "watt", "puissance"])
    hc = _find_col(df.columns, {"hr", "bpm", "fc", "heartrate", "heart_rate"}, ["heart", "cardi"])
    out = {"avg_power": None, "avg_hr": None, "rows": int(len(df))}
    if pc is not None:
        p = pd.to_numeric(df[pc], errors="coerce").dropna()
        p = p[p > 0]
        if len(p):
            out["avg_power"] = float(p.mean())
    if hc is not None:
        hr = pd.to_numeric(df[hc], errors="coerce").dropna()
        hr = hr[hr > 30]
        if len(hr):
            out["avg_hr"] = float(hr.mean())
    return out


# ------------------------------------------------------------------------------
#  STOCKAGE LOCAL (profils, historique, images)
# ------------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("VELOFIT_DATA", "velofit_data"))


def safe_name(name):
    n = re.sub(r"[^\w\-]+", "_", (name or "").strip(), flags=re.UNICODE).strip("_")
    return n[:48] or "invite"


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except Exception:
        return default


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(path)


def _base(scope=""):
    """Dossier des profils. Avec un « scope » (nom d'utilisateur), chaque compte a son espace isolé."""
    if scope:
        return DATA_DIR / "users" / safe_name(scope) / "profiles"
    return DATA_DIR / "profiles"


def _pdir(name, scope=""):
    return _base(scope) / safe_name(name)


def list_profiles(scope=""):
    base = _base(scope)
    if not base.exists():
        return []
    out = []
    for d in sorted(base.iterdir()):
        if (d / "profile.json").exists():
            out.append(_read_json(d / "profile.json", {}).get("name", d.name))
    return out


def load_profile(name, scope=""):
    return _read_json(_pdir(name, scope) / "profile.json", {})


def save_profile(name, data, scope=""):
    data = dict(data)
    data["name"] = (name or "invité").strip() or "invité"
    _write_json(_pdir(name, scope) / "profile.json", data)


def load_history(name, scope=""):
    return _read_json(_pdir(name, scope) / "history.json", [])


def add_history(name, entry, png_bytes=None, scope=""):
    d = _pdir(name, scope)
    hist = load_history(name, scope)
    entry = dict(entry)
    entry["id"] = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    entry["date"] = datetime.now().isoformat(timespec="seconds")
    if png_bytes:
        (d / "images").mkdir(parents=True, exist_ok=True)
        fname = f"{entry['id']}.png"
        (d / "images" / fname).write_bytes(png_bytes)
        entry["image"] = fname
    hist.append(entry)
    _write_json(d / "history.json", hist)
    return entry


def update_history_entry(name, entry_id, updates, scope=""):
    hist = load_history(name, scope)
    for e in hist:
        if e.get("id") == entry_id:
            e.update(updates)
    _write_json(_pdir(name, scope) / "history.json", hist)


def delete_history_entry(name, entry_id, scope=""):
    hist = load_history(name, scope)
    keep = []
    for e in hist:
        if e.get("id") == entry_id:
            if e.get("image"):
                try:
                    (_pdir(name, scope) / "images" / Path(e["image"]).name).unlink()
                except Exception:
                    pass
        else:
            keep.append(e)
    _write_json(_pdir(name, scope) / "history.json", keep)


def load_history_image(name, entry, scope=""):
    if not entry.get("image"):
        return None
    p = _pdir(name, scope) / "images" / Path(entry["image"]).name
    return p.read_bytes() if p.exists() else None


def profile_summary(name, scope=""):
    hist = load_history(name, scope)
    prof = load_profile(name, scope)
    last = hist[-1] if hist else None
    return {"name": name, "n": len(hist), "last_score": last["score"] if last else None,
            "last_date": last["date"][:10] if last else None, "discipline": prof.get("discipline", "—"),
            "target": prof.get("target_score")}


# ------------------------------------------------------------------------------
#  RAPPORTS (Markdown, HTML, PDF)
# ------------------------------------------------------------------------------
def _plain(s):
    s = re.sub(r"<[^>]+>", "", str(s))
    return _html.unescape(s)


def png_bytes(rgb):
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return buf.tobytes() if ok else b""


def assemble_report(ctx, m, ev, ranges, score, recs, quality, annotated_rgb, studio="", client="", logo_bytes=None, extras=None):
    title, sub = verdict_for(score)
    rows = []
    for k in ORDER:
        rows.append(dict(label=META[k]["label"], value=f"{m[k]:.1f}°", target=f"{ranges[k][0]}–{ranges[k][1]}°",
                         status=STATUS[ev[k]["status"]][1], color=STATUS[ev[k]["status"]][0]))
    todo = [dict(title=r["title"], diag=_plain(r["diag"]), actions=[_plain(a) for a in r["actions"]])
            for r in recs if r["status"] != "ok"]
    return dict(
        studio=studio or "VeloFit AI Studio", client=client or "Cycliste", date=datetime.now().strftime("%d/%m/%Y"),
        discipline=ctx["discipline"], goal=ctx["goal"], flex=ctx["flex"], height=ctx["height"],
        score=float(score), verdict=title, verdict_sub=sub, quality=float(quality), rows=rows, todo=todo,
        image_png=png_bytes(annotated_rgb), logo=logo_bytes, extras=[(t, _plain(x)) for t, x in (extras or [])],
        disclaimer="Outil indicatif : ne remplace pas l'avis d'un professionnel du bike-fitting ni d'un professionnel de santé en cas de douleur persistante.",
    )


def report_markdown(r):
    lines = [f"# Rapport {r['studio']}", "", f"*{r['client']} — {r['date']}*", "",
             f"**Discipline :** {r['discipline']} · **Objectif :** {r['goal']} · **Souplesse :** {r['flex']} · **Taille :** {r['height']} cm  ",
             f"**Score postural :** {r['score']:.0f}/100 ({r['verdict']}) · **Qualité de la prise de vue :** {r['quality']:.0f}/100", "",
             "## Mesures", "", "| Mesure | Valeur | Cible | Statut |", "|---|---|---|---|"]
    for row in r["rows"]:
        lines.append(f"| {row['label']} | {row['value']} | {row['target']} | {row['status']} |")
    lines += ["", "## Plan d'action", ""]
    if not r["todo"]:
        lines.append("Aucun réglage prioritaire : votre position est dans les plages cibles.")
    for i, t in enumerate(r["todo"], 1):
        lines.append(f"{i}. **{t['title']}** — {t['diag']}")
        for a in t["actions"]:
            lines.append(f"   - {a}")
    for title, text in r["extras"]:
        lines += ["", f"## {title}", "", text]
    lines += ["", "---", f"*{r['disclaimer']}*"]
    return "\n".join(lines)


def report_html(r):
    e = _html.escape
    img = base64.b64encode(r["image_png"]).decode() if r["image_png"] else ""
    logo = ("<img class='logo' src='data:image/png;base64," + base64.b64encode(r["logo"]).decode() + "'>") if r["logo"] else ""
    rows = "".join(f"<tr><td>{e(x['label'])}</td><td><b>{e(x['value'])}</b></td><td>{e(x['target'])}</td>"
                   f"<td><span class='pill' style='background:{x['color']}'>{e(x['status'])}</span></td></tr>" for x in r["rows"])
    todo = "".join(f"<li><b>{e(t['title'])}</b><br>{e(t['diag'])}<ul>" + "".join(f"<li>{e(a)}</li>" for a in t["actions"]) + "</ul></li>" for t in r["todo"]) \
        or "<li>Aucun réglage prioritaire : tous les angles sont dans les plages cibles.</li>"
    extras = "".join(f"<h2>{e(t)}</h2><p>{e(x)}</p>" for t, x in r["extras"])
    col = "#34d399" if r["score"] >= 80 else ("#fbbf24" if r["score"] >= 60 else "#fb7185")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Rapport {e(r['studio'])}</title>
<style>
body{{font-family:Inter,Arial,sans-serif;color:#0f172a;margin:0;background:#f1f5f9}}
.page{{max-width:860px;margin:24px auto;background:#fff;padding:0 0 32px;box-shadow:0 10px 40px rgba(0,0,0,.12)}}
header{{background:#0b1020;color:#fff;padding:26px 36px;display:flex;align-items:center;gap:20px}}
header h1{{margin:0;font-size:1.5rem}} header p{{margin:2px 0 0;color:#94a3b8}}
.logo{{height:56px}} section{{padding:0 36px}}
.score{{display:flex;gap:24px;align-items:center;margin:24px 0}}
.ring{{width:110px;height:110px;border-radius:50%;background:{col};color:#fff;display:grid;place-items:center;font-size:2.2rem;font-weight:700}}
table{{width:100%;border-collapse:collapse;margin:8px 0 20px}} td,th{{padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:left}}
.pill{{color:#fff;border-radius:99px;padding:3px 10px;font-size:.78rem}} img.main{{width:100%;border-radius:12px;margin:8px 0}}
li{{margin-bottom:8px}} .note{{font-size:.8rem;color:#64748b;border-top:1px solid #e2e8f0;padding-top:12px;margin-top:20px}}
@media print{{body{{background:#fff}}.page{{box-shadow:none;margin:0}}}}
</style></head><body><div class="page">
<header>{logo}<div><h1>{e(r['studio'])}</h1><p>{e(r['client'])} · {e(r['date'])}</p></div></header>
<section><div class="score"><div class="ring">{r['score']:.0f}</div>
<div><h2 style="margin:0">{e(r['verdict'])}</h2><p>{e(r['verdict_sub'])}</p>
<p style="color:#64748b">{e(r['discipline'])} · objectif {e(r['goal'])} · souplesse {e(r['flex'])} · {r['height']} cm · qualité photo {r['quality']:.0f}/100</p></div></div>
{('<img class="main" src="data:image/png;base64,' + img + '">') if img else ''}
<h2>Mesures</h2><table><tr><th>Mesure</th><th>Valeur</th><th>Cible</th><th>Statut</th></tr>{rows}</table>
<h2>Plan d'action</h2><ol>{todo}</ol>{extras}
<p class="note">{e(r['disclaimer'])}</p></section></div></body></html>"""


def _pdf_text(s):
    rep = {"–": "-", "—": "-", "→": "->", "≈": "~", "≥": ">=", "≤": "<=", "’": "'", "…": "...", "±": "+/-", "·": "-", "•": "-"}
    s = _plain(s)
    for a, b in rep.items():
        s = s.replace(a, b)
    return s


def _font(size, bold=False):
    from PIL import ImageFont
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf", "Helvetica.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def report_pdf(r):
    """PDF A4 sans dépendance externe (Pillow) : texte rendu en image à 150 dpi."""
    from PIL import Image, ImageDraw

    W, H, M = 1240, 1754, 70
    NAVY, TXT, MUT, LINE = (11, 16, 32), (15, 23, 42), (100, 116, 139), (226, 232, 240)
    pages = []
    state = {}

    def new_page(first=False):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        pages.append(img)
        state["img"], state["d"] = img, d
        if first:
            d.rectangle([0, 0, W, 190], fill=NAVY)
            x = M
            if r.get("logo"):
                try:
                    lg = Image.open(io.BytesIO(r["logo"])).convert("RGBA")
                    ratio = 100 / lg.height
                    lg = lg.resize((max(1, int(lg.width * ratio)), 100))
                    img.paste(lg, (M, 45), lg)
                    x = M + lg.width + 30
                except Exception:
                    pass
            d.text((x, 52), _pdf_text(r["studio"]), font=_font(46, True), fill="white")
            d.text((x, 112), _pdf_text(f"{r['client']}  -  {r['date']}"), font=_font(28), fill=(148, 163, 184))
            state["y"] = 230
        else:
            d.rectangle([0, 0, W, 70], fill=NAVY)
            d.text((M, 20), _pdf_text(r["studio"]), font=_font(26, True), fill="white")
            state["y"] = 110

    def ensure(hh):
        if state["y"] + hh > H - 90:
            new_page()

    def text(s, font, fill=TXT, x=M, width=W - 2 * M, gap=10):
        words = _pdf_text(s).split()
        line = ""
        d = state["d"]
        for wd in words + [None]:
            test = (line + " " + wd).strip() if wd else line
            if wd is None or d.textlength(test, font=font) > width:
                if line:
                    ensure(font.size + gap + 6)
                    state["d"].text((x, state["y"]), line, font=font, fill=fill)
                    state["y"] += font.size + gap
                line = wd or ""
            else:
                line = test

    new_page(first=True)
    d = state["d"]
    col = (52, 211, 153) if r["score"] >= 80 else ((251, 191, 36) if r["score"] >= 60 else (251, 113, 133))
    cx, cy, rad = M + 110, state["y"] + 110, 110
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(226, 232, 240))
    d.pieslice([cx - rad, cy - rad, cx + rad, cy + rad], -90, -90 + 360 * r["score"] / 100.0, fill=col)
    d.ellipse([cx - 82, cy - 82, cx + 82, cy + 82], fill="white")
    sc = f"{r['score']:.0f}"
    d.text((cx - d.textlength(sc, font=_font(64, True)) / 2, cy - 44), sc, font=_font(64, True), fill=TXT)
    d.text((cx - 22, cy + 26), "/ 100", font=_font(22), fill=MUT)
    state["d"].text((cx + rad + 40, state["y"] + 40), _pdf_text(r["verdict"]), font=_font(40, True), fill=TXT)
    ytxt = state["y"] + 100
    state["y"] = ytxt
    text(r["verdict_sub"], _font(24), MUT, x=cx + rad + 40, width=W - (cx + rad + 40) - M)
    state["y"] = max(state["y"], cy + rad + 30)
    text(f"{r['discipline']} - objectif {r['goal']} - souplesse {r['flex']} - {r['height']} cm - qualité photo {r['quality']:.0f}/100", _font(22), MUT)
    state["y"] += 10

    if r["image_png"]:
        try:
            im = Image.open(io.BytesIO(r["image_png"])).convert("RGB")
            maxw, maxh = W - 2 * M, 640
            ratio = min(maxw / im.width, maxh / im.height)
            im = im.resize((int(im.width * ratio), int(im.height * ratio)))
            ensure(im.height + 20)
            state["img"].paste(im, ((W - im.width) // 2, state["y"]))
            state["y"] += im.height + 30
        except Exception:
            pass

    ensure(60 + 54 * (len(r["rows"]) + 1))
    d = state["d"]
    d.text((M, state["y"]), "Mesures", font=_font(36, True), fill=TXT)
    state["y"] += 62
    cols = [M, M + 540, M + 740, M + 940]
    for x, label in zip(cols, ("Mesure", "Valeur", "Cible", "Statut")):
        d.text((x, state["y"]), label, font=_font(22, True), fill=MUT)
    state["y"] += 38
    for row in r["rows"]:
        d.line([M, state["y"] - 6, W - M, state["y"] - 6], fill=LINE, width=2)
        d.text((cols[0], state["y"]), _pdf_text(row["label"]), font=_font(26), fill=TXT)
        d.text((cols[1], state["y"]), _pdf_text(row["value"]), font=_font(26, True), fill=TXT)
        d.text((cols[2], state["y"]), _pdf_text(row["target"]), font=_font(26), fill=TXT)
        rgb = tuple(int(row["color"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        d.rounded_rectangle([cols[3], state["y"], cols[3] + 200, state["y"] + 36], radius=18, fill=rgb)
        d.text((cols[3] + 16, state["y"] + 4), _pdf_text(row["status"]), font=_font(21, True), fill="white")
        state["y"] += 54
    state["y"] += 20

    ensure(120)
    state["d"].text((M, state["y"]), "Plan d'action", font=_font(36, True), fill=TXT)
    state["y"] += 64
    if not r["todo"]:
        text("Aucun réglage prioritaire : tous les angles sont dans les plages cibles.", _font(26))
    for i, t in enumerate(r["todo"], 1):
        ensure(140)
        text(f"{i}. {t['title']}", _font(28, True))
        text(t["diag"], _font(23), MUT, x=M + 30, width=W - 2 * M - 30)
        for a in t["actions"]:
            text("- " + a, _font(23), TXT, x=M + 30, width=W - 2 * M - 30, gap=8)
        state["y"] += 14
    for title, body in r["extras"]:
        ensure(140)
        state["y"] += 10
        state["d"].text((M, state["y"]), _pdf_text(title), font=_font(32, True), fill=TXT)
        state["y"] += 56
        text(body, _font(23), TXT)
    ensure(100)
    state["y"] += 20
    text(r["disclaimer"], _font(20), MUT)
    for n, img in enumerate(pages, 1):
        ImageDraw.Draw(img).text((W - M - 80, H - 60), f"{n} / {len(pages)}", font=_font(20), fill=MUT)
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:], resolution=150.0)
    return buf.getvalue()
