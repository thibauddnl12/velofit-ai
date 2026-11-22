# ==============================================================================
#  cloud_store.py — sauvegarde automatique des données dans un dépôt GitHub privé
#
#  Pourquoi : sur Streamlit Community Cloud, le disque est effacé à chaque redémarrage.
#  Les comptes, profils et historiques (dossier VELOFIT_DATA) sont donc recopiés dans un
#  dépôt GitHub PRIVÉ après chaque modification, et rapatriés au démarrage.
#
#  Secrets attendus (variables d'environnement ou « Secrets » Streamlit) :
#    DATA_REPO    ex. "thibauddnl12/axon-data"   (dépôt privé, créé avec un README)
#    DATA_TOKEN   jeton GitHub « fine-grained » limité à ce dépôt, droit « Contents : Read and write »
#    DATA_BRANCH  facultatif, "main" par défaut
#  Sans ces secrets, rien ne change : l'application fonctionne comme avant (disque local seul).
#
#  Garde-fou : si les données n'ont pas pu être rapatriées au démarrage (réseau, jeton refusé…),
#  aucune sauvegarde n'est envoyée, pour ne jamais écraser la copie distante par une base vide.
#  Aucune dépendance Streamlit : `get` est une fonction nom -> valeur.
# ==============================================================================
from __future__ import annotations

import atexit
import base64
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import accounts as acc
import velofit_core as core

API = "https://api.github.com"
PREFIX = "data/"                    # dossier du dépôt qui reçoit les données
DEBOUNCE = 2.0                      # regroupe les modifications rapprochées en un seul envoi (secondes)
RETRY_AFTER = 30.0                  # nouvel essai après un échec d'envoi (secondes)
RESTORE_RETRY = 60.0                # nouvel essai de rapatriement après un échec (secondes)
MAX_FILE = 90 * 1024 * 1024         # GitHub refuse les fichiers de plus de 100 Mo
SKIP_DIRS = {"models"}              # modèles d'analyse téléchargés : inutile de les sauvegarder
DB = "accounts.db"

_lock = threading.RLock()
_dirty = threading.Event()
_cfg: dict | None = None
_remote: dict = {}                  # chemin relatif -> sha du fichier tel qu'il est dans le dépôt
_sha_cache: dict = {}               # chemin -> (taille, date de modification, sha) : évite de relire les fichiers inchangés
_worker: threading.Thread | None = None
_state = dict(mode="off", message="Sauvegarde automatique non configurée.", last_push=None, last_error="",
              files=0, restored=0, last_try=0.0)


class CloudError(Exception):
    pass


# ------------------------------------------------------------------------------
#  CONFIGURATION ET ÉTAT
# ------------------------------------------------------------------------------
def settings(get) -> dict | None:
    repo, token = (get("DATA_REPO") or "").strip().strip("/"), (get("DATA_TOKEN") or "").strip()
    if not (repo and token):
        return None
    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/"):]
    repo = repo.removesuffix(".git")
    return dict(repo=repo, token=token, branch=(get("DATA_BRANCH") or "main").strip() or "main")


def is_configured(get) -> bool:
    return settings(get) is not None


def status() -> dict:
    with _lock:
        return dict(_state)


def can_write() -> bool:
    return _state["mode"] == "ready"


# ------------------------------------------------------------------------------
#  APPELS À L'API GITHUB
# ------------------------------------------------------------------------------
def _req(method: str, path: str, body=None):
    """Appel à l'API GitHub. Retourne (code HTTP, JSON décodé ou None). Remplacé dans les tests."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {_cfg['token']}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "axon-app", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise CloudError(f"GitHub injoignable ({type(e).__name__}).") from e


def _call(method, path, body=None, ok=(200, 201)):
    code, js = _req(method, path, body)
    if code in ok:
        return js
    msg = (js or {}).get("message", "") if isinstance(js, dict) else ""
    if code == 401:
        raise CloudError("Jeton GitHub refusé (DATA_TOKEN) : il est peut-être expiré ou mal copié.")
    if code in (403, 404):
        raise CloudError(f"Dépôt « {_cfg['repo']} » introuvable, ou jeton sans accès en écriture (droit « Contents : Read and write »).")
    raise CloudError(f"Réponse inattendue de GitHub ({code}) : {msg or 'sans détail'}.")


def _repo(path: str) -> str:
    return f"/repos/{_cfg['repo']}{path}"


def _head() -> str:
    """Dernier commit de la branche. Un dépôt vide reçoit d'abord un README."""
    code, js = _req("GET", _repo(f"/git/ref/heads/{_cfg['branch']}"))
    if code == 200:
        return js["object"]["sha"]
    if code in (404, 409):
        info_code, info = _req("GET", _repo(""))
        if info_code != 200:
            _call("GET", _repo(""))                                   # lève l'erreur explicite (dépôt introuvable / jeton)
        readme = ("# Données Axon\n\nSauvegarde automatique de l'application Axon. Ce dépôt doit rester **privé** : "
                  "il contient les comptes (mots de passe hachés) et les photos des utilisateurs.\n")
        _call("PUT", _repo("/contents/README.md"), {"message": "Initialisation", "branch": _cfg["branch"],
                                                     "content": base64.b64encode(readme.encode()).decode()})
        return _call("GET", _repo(f"/git/ref/heads/{_cfg['branch']}"))["object"]["sha"]
    _call("GET", _repo(f"/git/ref/heads/{_cfg['branch']}"))
    raise CloudError("Branche introuvable.")


def _git_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# ------------------------------------------------------------------------------
#  FICHIERS LOCAUX
# ------------------------------------------------------------------------------
def _skip(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (rel.split("/", 1)[0] in SKIP_DIRS or (name.startswith(DB) and name != DB) or name.endswith((".tmp", ".cloudtmp")))


def _local_files() -> dict:
    """chemin relatif -> (sha, lecteur de contenu). La base de comptes est copiée de façon cohérente (sauvegarde SQLite)."""
    root = core.DATA_DIR
    out = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if _skip(rel):
            continue
        if rel == DB:
            data = acc.backup_bytes()
            out[rel] = (_git_sha(data), lambda d=data: d)
            continue
        st_ = p.stat()
        if st_.st_size > MAX_FILE:
            continue
        key = (st_.st_size, st_.st_mtime_ns)
        cached = _sha_cache.get(rel)
        if cached and cached[0] == key:
            sha = cached[1]
        else:
            sha = _git_sha(p.read_bytes())
            _sha_cache[rel] = (key, sha)
        out[rel] = (sha, lambda q=p: q.read_bytes())
    return out


def _write_local(rel: str, data: bytes):
    dest = core.DATA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if rel == DB:
        for suffix in ("-wal", "-shm"):
            try:
                os.unlink(str(dest) + suffix)
            except OSError:
                pass
    tmp = dest.with_name(dest.name + ".cloudtmp")
    tmp.write_bytes(data)
    tmp.replace(dest)


# ------------------------------------------------------------------------------
#  RAPATRIEMENT AU DÉMARRAGE
# ------------------------------------------------------------------------------
def _restore():
    """Au démarrage, le dépôt fait foi : chaque fichier du dépôt absent ou différent en local est rapatrié.
    (Toute modification est envoyée dans les 2 secondes : la copie du dépôt est la plus récente. Cela évite aussi qu'une base
    créée pendant une panne de GitHub, avec le seul compte administrateur, remplace les vrais comptes.)
    Les fichiers présents seulement en local sont gardés et seront envoyés."""
    head = _head()
    tree = _call("GET", _repo(f"/git/trees/{head}?recursive=1"))
    if tree.get("truncated"):
        raise CloudError("Le dépôt de sauvegarde contient trop de fichiers pour être relu en une fois.")
    remote = {e["path"][len(PREFIX):]: e["sha"] for e in tree.get("tree", [])
              if e.get("type") == "blob" and e["path"].startswith(PREFIX) and not _skip(e["path"][len(PREFIX):])}
    todo = []
    for rel, sha in remote.items():
        p = core.DATA_DIR / rel
        if rel == DB:
            todo.append((rel, sha))               # la base locale peut être ouverte : on la remplace toujours par celle du dépôt
        elif not p.exists() or _git_sha(p.read_bytes()) != sha:
            todo.append((rel, sha))

    def fetch(item):
        rel, sha = item
        js = _call("GET", _repo(f"/git/blobs/{sha}"))
        data = base64.b64decode(js.get("content", ""))
        if _git_sha(data) != sha:
            raise CloudError(f"Fichier reçu incomplet : {rel}.")
        return rel, data

    files = []
    if todo:
        with ThreadPoolExecutor(max_workers=8) as ex:
            files = list(ex.map(fetch, todo))
    db = [f for f in files if f[0] == DB]
    for rel, data in [f for f in files if f[0] != DB] + db:           # la base de comptes en dernier
        _write_local(rel, data)
    _remote.clear()
    _remote.update(remote)
    return len(files)


def start(get) -> dict:
    """À appeler à chaque affichage (coût nul après le premier) : rapatrie les données au démarrage puis lance l'envoi automatique."""
    global _cfg, _worker
    if _cfg is not None and _state["mode"] in ("ready", "off"):        # cas courant : rien à faire, sans attendre un envoi en cours
        return dict(_state)
    with _lock:
        if _state["mode"] in ("ready", "off") and _cfg is not None:
            return status()
        cfg = settings(get)
        if cfg is None:
            _cfg = {}
            _state.update(mode="off", message="Sauvegarde automatique non configurée : les données sont perdues à chaque redémarrage.")
            return status()
        if _state["mode"] == "error" and time.time() - _state["last_try"] < RESTORE_RETRY:
            return status()
        _cfg = cfg
        _state["last_try"] = time.time()
        try:
            n = _restore()
        except CloudError as e:
            _state.update(mode="error", last_error=str(e),
                          message="Données non rapatriées : la sauvegarde automatique est suspendue pour ne pas écraser la copie distante. " + str(e))
            return status()
        _state.update(mode="ready", restored=n, last_error="", files=len(_remote),
                      message=f"Sauvegarde automatique active (dépôt {cfg['repo']}).")
        if _register not in core.CHANGE_HOOKS:
            core.CHANGE_HOOKS.append(_register)
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_loop, name="axon-sauvegarde", daemon=True)
            _worker.start()
        _dirty.set()                         # envoie les éventuelles données locales plus récentes
        return status()


# ------------------------------------------------------------------------------
#  ENVOI DES MODIFICATIONS
# ------------------------------------------------------------------------------
def _register():
    _dirty.set()


def flush() -> int:
    """Envoie les fichiers modifiés depuis le dernier envoi, en un seul commit. Retourne le nombre de fichiers envoyés ou supprimés."""
    with _lock:
        if _state["mode"] != "ready":
            return 0
        local = _local_files()
        changed = {rel: v for rel, v in local.items() if _remote.get(rel) != v[0]}
        removed = [rel for rel in _remote if rel not in local]
        if not changed and not removed:
            return 0
        for attempt in range(2):
            head = _head()
            base = _call("GET", _repo(f"/git/commits/{head}"))["tree"]["sha"]
            entries = []
            for rel, (sha, read) in changed.items():
                blob = _call("POST", _repo("/git/blobs"), {"content": base64.b64encode(read()).decode(), "encoding": "base64"})
                entries.append({"path": PREFIX + rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            for rel in removed:
                entries.append({"path": PREFIX + rel, "mode": "100644", "type": "blob", "sha": None})
            tree = _call("POST", _repo("/git/trees"), {"base_tree": base, "tree": entries})
            commit = _call("POST", _repo("/git/commits"), {"message": f"Sauvegarde {datetime.now():%Y-%m-%d %H:%M:%S}",
                                                           "tree": tree["sha"], "parents": [head]})
            code, js = _req("PATCH", _repo(f"/git/refs/heads/{_cfg['branch']}"), {"sha": commit["sha"], "force": False})
            if code == 200:
                for rel, (sha, _r) in changed.items():
                    _remote[rel] = sha
                for rel in removed:
                    _remote.pop(rel, None)
                _state.update(last_push=datetime.now(), last_error="", files=len(_remote))
                return len(changed) + len(removed)
            if code != 422 or attempt:
                raise CloudError(f"Mise à jour du dépôt refusée ({code}).")
        return 0


def _loop():
    while True:
        _dirty.wait()
        time.sleep(DEBOUNCE)
        _dirty.clear()
        try:
            flush()
        except Exception as e:  # réseau, jeton expiré… : on garde les données en local et on réessaie
            with _lock:
                _state["last_error"] = f"{type(e).__name__} : {e}" if not isinstance(e, CloudError) else str(e)
            print(f"[Axon] Sauvegarde automatique en échec : {_state['last_error']}", flush=True)
            time.sleep(RETRY_AFTER)
            _dirty.set()


def _at_exit():
    try:
        if _state["mode"] == "ready" and _dirty.is_set():
            flush()
    except Exception:
        pass


atexit.register(_at_exit)
