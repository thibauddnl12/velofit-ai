# ==============================================================================
#  accounts.py — comptes, quotas d'analyses, abonnements et paiements (SQLite)
#  Aucune dépendance Streamlit : testable seul.
# ==============================================================================
from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import velofit_core as core

USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERS = 310_000
MAX_FAILS = 5
LOCK_MINUTES = 10

DEFAULT_SETTINGS = {
    "free_credits": "3",          # analyses gratuites offertes à chaque nouveau compte
    "allow_signup": "1",          # 1 = les visiteurs peuvent créer un compte eux-mêmes
    "plan_name": "Abonnement mensuel",
    "plan_price": "9,90 € / mois",
    "plan_days": "30",            # durée accordée par paiement
    "payment_link": "",           # lien de paiement Stripe (Payment Link, paiement unique)
    "stripe_link_id": "",         # optionnel : identifiant plink_... pour limiter la recherche
    "contact": "",                # e-mail ou message affiché sur la page d'abonnement
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  username TEXT PRIMARY KEY, email TEXT DEFAULT '', pw_hash TEXT NOT NULL, salt TEXT NOT NULL, iters INTEGER NOT NULL,
  role TEXT NOT NULL DEFAULT 'user', active INTEGER NOT NULL DEFAULT 1,
  free_credits INTEGER NOT NULL DEFAULT 3, free_used INTEGER NOT NULL DEFAULT 0,
  sub_until TEXT DEFAULT NULL, created_at TEXT NOT NULL, last_login TEXT DEFAULT NULL,
  fails INTEGER NOT NULL DEFAULT 0, locked_until TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, file_hash TEXT NOT NULL, ts TEXT NOT NULL, kind TEXT NOT NULL,
  UNIQUE(username, file_hash)
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(
  session_id TEXT PRIMARY KEY, username TEXT NOT NULL, amount INTEGER, currency TEXT, ts TEXT NOT NULL, days INTEGER NOT NULL
);
"""


# ------------------------------------------------------------------------------
#  OUTILS
# ------------------------------------------------------------------------------
def now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _parse(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def _conn():
    path = core.DATA_DIR / "accounts.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=15, isolation_level=None)  # transactions gérées à la main
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    con.executescript(SCHEMA)
    return con


@contextlib.contextmanager
def _db():
    con = _conn()
    try:
        yield con
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def _hash(password: str, salt: bytes, iters: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters).hex()


def clean_username(u: str) -> str:
    return (u or "").strip().lower()


def check_username(u: str):
    if not USERNAME_RE.match(u):
        return "Identifiant invalide : 3 à 32 caractères, lettres minuscules, chiffres, « _ » ou « - »."
    return None


def check_password(p: str):
    if len(p or "") < 8:
        return "Mot de passe trop court : 8 caractères minimum."
    if len(p) > 200:
        return "Mot de passe trop long."
    return None


# ------------------------------------------------------------------------------
#  RÉGLAGES
# ------------------------------------------------------------------------------
def get_settings() -> dict:
    out = dict(DEFAULT_SETTINGS)
    with _db() as con:
        for r in con.execute("SELECT key, value FROM settings"):
            out[r["key"]] = r["value"]
    return out


def set_setting(key: str, value) -> None:
    if key not in DEFAULT_SETTINGS:
        raise KeyError(key)
    with _db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def setting_int(cfg: dict, key: str) -> int:
    try:
        return max(0, int(cfg.get(key, DEFAULT_SETTINGS[key])))
    except (TypeError, ValueError):
        return int(DEFAULT_SETTINGS[key])


# ------------------------------------------------------------------------------
#  COMPTES
# ------------------------------------------------------------------------------
def create_user(username, password, role="user", free_credits=None, sub_days=0, email="", check_signup=False):
    """Crée un compte. Retourne (ok, message)."""
    u = clean_username(username)
    err = check_username(u) or check_password(password)
    if err:
        return False, err
    email = (email or "").strip()
    if email and not EMAIL_RE.match(email):
        return False, "Adresse e-mail invalide."
    if role not in ("user", "admin"):
        return False, "Rôle inconnu."
    cfg = get_settings()
    if check_signup and cfg["allow_signup"] != "1":
        return False, "Les inscriptions sont fermées. Contactez l'administrateur."
    fc = setting_int(cfg, "free_credits") if free_credits is None else max(0, int(free_credits))
    salt = secrets.token_bytes(16)
    until = _iso(now() + timedelta(days=int(sub_days))) if sub_days and int(sub_days) > 0 else None
    try:
        with _db() as con:
            con.execute(
                "INSERT INTO users(username,email,pw_hash,salt,iters,role,free_credits,sub_until,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (u, email, _hash(password, salt, PBKDF2_ITERS), salt.hex(), PBKDF2_ITERS, role, fc, until, _iso(now())))
    except sqlite3.IntegrityError:
        return False, "Cet identifiant existe déjà."
    return True, f"Compte « {u} » créé."


def get_user(username) -> dict | None:
    with _db() as con:
        r = con.execute("SELECT * FROM users WHERE username=?", (clean_username(username),)).fetchone()
    return dict(r) if r else None


def list_users() -> list[dict]:
    with _db() as con:
        rows = con.execute(
            "SELECT u.*, (SELECT COUNT(*) FROM usage x WHERE x.username=u.username) AS n_analyses FROM users u ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def authenticate(username, password):
    """Retourne (utilisateur | None, message). Verrouille le compte après trop d'échecs."""
    u = clean_username(username)
    with _db() as con:
        r = con.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if r is None:
            _hash(password or "", b"\x00" * 16, PBKDF2_ITERS)  # temps constant approximatif
            return None, "Identifiant ou mot de passe incorrect."
        lock = _parse(r["locked_until"])
        if lock and lock > now():
            mins = int((lock - now()).total_seconds() // 60) + 1
            return None, f"Trop de tentatives. Réessayez dans {mins} min."
        calc = _hash(password or "", bytes.fromhex(r["salt"]), r["iters"])
        if not hmac.compare_digest(calc, r["pw_hash"]):
            fails = r["fails"] + 1
            locked = _iso(now() + timedelta(minutes=LOCK_MINUTES)) if fails >= MAX_FAILS else None
            con.execute("UPDATE users SET fails=?, locked_until=? WHERE username=?", (0 if locked else fails, locked, u))
            return None, "Identifiant ou mot de passe incorrect."
        if not r["active"]:
            return None, "Ce compte est désactivé. Contactez l'administrateur."
        con.execute("UPDATE users SET fails=0, locked_until=NULL, last_login=? WHERE username=?", (_iso(now()), u))
        return dict(r), "ok"


def set_password(username, new_password):
    err = check_password(new_password)
    if err:
        return False, err
    salt = secrets.token_bytes(16)
    with _db() as con:
        cur = con.execute("UPDATE users SET pw_hash=?, salt=?, iters=?, fails=0, locked_until=NULL WHERE username=?",
                          (_hash(new_password, salt, PBKDF2_ITERS), salt.hex(), PBKDF2_ITERS, clean_username(username)))
    return (cur.rowcount > 0), ("Mot de passe modifié." if cur.rowcount else "Compte introuvable.")


def change_own_password(username, old, new):
    user, msg = authenticate(username, old)
    if user is None:
        return False, "Mot de passe actuel incorrect."
    return set_password(username, new)


def set_active(username, active: bool):
    with _db() as con:
        con.execute("UPDATE users SET active=? WHERE username=?", (1 if active else 0, clean_username(username)))


def add_credits(username, n: int):
    with _db() as con:
        con.execute("UPDATE users SET free_credits=MAX(0, free_credits+?) WHERE username=?", (int(n), clean_username(username)))


def set_subscription(username, days: int):
    """Prolonge l'abonnement de `days` jours à partir de la date de fin actuelle (ou d'aujourd'hui)."""
    u = clean_username(username)
    with _db() as con:
        con.execute("BEGIN IMMEDIATE")
        r = con.execute("SELECT sub_until FROM users WHERE username=?", (u,)).fetchone()
        if r is None:
            con.execute("ROLLBACK")
            return None
        base = max(now(), _parse(r["sub_until"]) or now())
        until = _iso(base + timedelta(days=int(days)))
        con.execute("UPDATE users SET sub_until=? WHERE username=?", (until, u))
        con.execute("COMMIT")
    return until


def clear_subscription(username):
    with _db() as con:
        con.execute("UPDATE users SET sub_until=NULL WHERE username=?", (clean_username(username),))


def delete_user(username, delete_data=True):
    u = clean_username(username)
    with _db() as con:
        con.execute("DELETE FROM users WHERE username=?", (u,))
        con.execute("DELETE FROM usage WHERE username=?", (u,))
    if delete_data:
        shutil.rmtree(core.DATA_DIR / "users" / core.safe_name(u), ignore_errors=True)


def ensure_admin(username, password):
    """Crée ou met à jour le compte administrateur à partir des secrets / variables d'environnement."""
    u = clean_username(username)
    err = check_username(u) or check_password(password)
    if err:
        return False, "Identifiants administrateur invalides : " + err
    cur = get_user(u)
    if cur is None:
        ok, msg = create_user(u, password, role="admin", free_credits=0)
        return ok, msg
    calc = _hash(password, bytes.fromhex(cur["salt"]), cur["iters"])
    if not hmac.compare_digest(calc, cur["pw_hash"]):
        set_password(u, password)
    with _db() as con:
        con.execute("UPDATE users SET role='admin', active=1 WHERE username=?", (u,))
    return True, "Administrateur prêt."


def has_admin() -> bool:
    with _db() as con:
        return con.execute("SELECT 1 FROM users WHERE role='admin' AND active=1 LIMIT 1").fetchone() is not None


# ------------------------------------------------------------------------------
#  QUOTAS ET ABONNEMENTS
# ------------------------------------------------------------------------------
def status(user: dict) -> dict:
    until = _parse(user.get("sub_until"))
    sub_active = bool(until and until > now())
    free_left = max(0, int(user["free_credits"]) - int(user["free_used"]))
    is_admin = user["role"] == "admin"
    return dict(is_admin=is_admin, sub_active=sub_active, sub_until=until, free_total=int(user["free_credits"]),
                free_used=int(user["free_used"]), free_left=free_left, can_analyze=is_admin or sub_active or free_left > 0)


def use_analysis(username, file_hash, kind="photo"):
    """Autorise (et décompte) l'analyse d'un fichier. Retourne (ok, raison, nouveau_decompte).

    Une même image/vidéo déjà analysée par ce compte ne coûte rien de plus."""
    u = clean_username(username)
    with _db() as con:
        con.execute("BEGIN IMMEDIATE")
        r = con.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if r is None or not r["active"]:
            con.execute("ROLLBACK")
            return False, "inactive", False
        if con.execute("SELECT 1 FROM usage WHERE username=? AND file_hash=?", (u, file_hash)).fetchone():
            con.execute("COMMIT")
            return True, "already", False
        st = status(dict(r))
        if st["is_admin"]:
            reason = "admin"
        elif st["sub_active"]:
            reason = "sub"
        elif st["free_left"] > 0:
            reason = "free"
            con.execute("UPDATE users SET free_used=free_used+1 WHERE username=?", (u,))
        else:
            con.execute("ROLLBACK")
            return False, "quota", False
        con.execute("INSERT INTO usage(username,file_hash,ts,kind) VALUES(?,?,?,?)", (u, file_hash, _iso(now()), reason))
        con.execute("COMMIT")
    return True, reason, True


def stats() -> dict:
    with _db() as con:
        n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_sub = con.execute("SELECT COUNT(*) FROM users WHERE sub_until > ?", (_iso(now()),)).fetchone()[0]
        n_an = con.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
        n_7 = con.execute("SELECT COUNT(*) FROM usage WHERE ts > ?", (_iso(now() - timedelta(days=7)),)).fetchone()[0]
        n_pay = con.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    return dict(users=n_users, subscribers=n_sub, analyses=n_an, analyses_7d=n_7, payments=n_pay)


# ------------------------------------------------------------------------------
#  PAIEMENTS STRIPE (sans serveur de webhook : vérification à la demande)
# ------------------------------------------------------------------------------
def payment_url(cfg: dict, username: str, email: str = "") -> str:
    link = (cfg.get("payment_link") or "").strip()
    if not link.startswith("https://"):
        return ""
    params = {"client_reference_id": clean_username(username)}
    if email:
        params["prefilled_email"] = email
    return link + ("&" if "?" in link else "?") + urllib.parse.urlencode(params)


def _stripe_get(path: str, params: dict, secret_key: str) -> dict:
    url = "https://api.stripe.com/v1/" + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    token = base64.b64encode((secret_key + ":").encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sync_payments(username, secret_key, cfg=None):
    """Cherche les paiements Stripe réussis portant l'identifiant du compte et prolonge l'abonnement.

    Chaque session Stripe n'est comptée qu'une fois. Retourne (nombre de nouveaux paiements, message)."""
    u = clean_username(username)
    cfg = cfg or get_settings()
    if not secret_key:
        return 0, "La vérification automatique n'est pas configurée : contactez l'administrateur."
    days = max(1, setting_int(cfg, "plan_days"))
    params = {"limit": 100, "created[gte]": int((now() - timedelta(days=90)).timestamp())}
    if cfg.get("stripe_link_id"):
        params["payment_link"] = cfg["stripe_link_id"]
    found, after = [], None
    try:
        for _ in range(5):
            p = dict(params)
            if after:
                p["starting_after"] = after
            data = _stripe_get("checkout/sessions", p, secret_key)
            items = data.get("data", [])
            found += items
            if not data.get("has_more") or not items:
                break
            after = items[-1]["id"]
    except Exception as exc:  # réseau, clé invalide…
        return 0, f"Impossible de joindre le service de paiement ({type(exc).__name__}). Réessayez plus tard."
    new = 0
    for s in found:
        if s.get("payment_status") != "paid" or s.get("status") != "complete":
            continue
        if clean_username(s.get("client_reference_id") or "") != u:
            continue
        try:
            with _db() as con:
                con.execute("INSERT INTO payments(session_id,username,amount,currency,ts,days) VALUES(?,?,?,?,?,?)",
                            (s["id"], u, s.get("amount_total"), s.get("currency"), _iso(now()), days))
        except sqlite3.IntegrityError:
            continue
        set_subscription(u, days)
        new += 1
    if new:
        return new, f"Paiement confirmé : abonnement prolongé de {days * new} jours."
    return 0, "Aucun nouveau paiement trouvé pour ce compte. Si vous venez de payer, patientez une minute puis réessayez."


def list_payments(limit=50) -> list[dict]:
    with _db() as con:
        rows = con.execute("SELECT * FROM payments ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------------------
#  SAUVEGARDE / RESTAURATION (utile sur un hébergement au disque éphémère)
# ------------------------------------------------------------------------------
def backup_bytes() -> bytes:
    """Copie cohérente de la base de comptes (comptes, quotas, abonnements, paiements, réglages)."""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = _conn()
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return Path(tmp).read_bytes()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def restore_from_bytes(data: bytes):
    """Remplace la base par une sauvegarde après vérification. Retourne (ok, message)."""
    if not data.startswith(b"SQLite format 3\x00"):
        return False, "Ce fichier n'est pas une sauvegarde valide."
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        con = sqlite3.connect(tmp)
        try:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"users", "usage", "settings", "payments"} <= tables:
                return False, "Sauvegarde incomplète : tables manquantes."
            n_admin = con.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        except sqlite3.DatabaseError:
            return False, "Sauvegarde illisible."
        finally:
            con.close()
        if n_admin < 1:
            return False, "Cette sauvegarde ne contient aucun administrateur."
        dest = core.DATA_DIR / "accounts.db"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.copyfile(dest, dest.with_name(f"accounts.db.avant-restauration-{now():%Y%m%d-%H%M%S}"))
        for suffix in ("-wal", "-shm"):
            try:
                os.unlink(str(dest) + suffix)
            except OSError:
                pass
        shutil.copyfile(tmp, dest)
        return True, f"Sauvegarde restaurée ({n_users} comptes)."
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
