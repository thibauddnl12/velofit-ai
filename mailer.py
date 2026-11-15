# ==============================================================================
#  mailer.py — envoi d'e-mails par SMTP (bibliothèque standard uniquement)
#
#  Secrets attendus (variables d'environnement ou « Secrets » Streamlit) :
#    SMTP_HOST      ex. "smtp.gmail.com"
#    SMTP_PORT      587 (STARTTLS, par défaut) ou 465 (SSL)
#    SMTP_USER      identifiant de la boîte d'envoi
#    SMTP_PASSWORD  mot de passe (pour Gmail : un « mot de passe d'application »)
#    SMTP_FROM      adresse d'expédition (facultatif : SMTP_USER par défaut)
#  Aucune dépendance Streamlit : `get` est une fonction nom -> valeur.
# ==============================================================================
from __future__ import annotations

import html as _html
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

APP_NAME = "VeloFit AI Studio"
TIMEOUT = 20


def settings(get) -> dict | None:
    """Réglages SMTP lus via `get`, ou None s'il en manque."""
    host, user, pw = (get("SMTP_HOST") or "").strip(), (get("SMTP_USER") or "").strip(), get("SMTP_PASSWORD") or ""
    if not (host and user and pw):
        return None
    try:
        port = int(str(get("SMTP_PORT") or "587").strip())
    except ValueError:
        port = 587
    sender = (get("SMTP_FROM") or "").strip() or user
    return dict(host=host, port=port, user=user, password=pw.replace(" ", "") if "gmail" in host.lower() else pw, sender=sender)


def is_configured(get) -> bool:
    return settings(get) is not None


def send(get, to: str, subject: str, text: str, html: str | None = None):
    """Envoie un e-mail. Retourne (ok, message lisible par l'administrateur)."""
    cfg = settings(get)
    if cfg is None:
        return False, "L'envoi d'e-mails n'est pas configuré (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((APP_NAME, cfg["sender"]))
    msg["To"] = to
    msg["Message-ID"] = make_msgid(domain=cfg["sender"].split("@")[-1] or None)
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    ctx = ssl.create_default_context()
    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=TIMEOUT, context=ctx) as srv:
                srv.login(cfg["user"], cfg["password"])
                srv.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=TIMEOUT) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.ehlo()
                srv.login(cfg["user"], cfg["password"])
                srv.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return False, ("Identifiants SMTP refusés. Avec Gmail, il faut activer la validation en deux étapes puis créer un "
                       "« mot de passe d'application » : le mot de passe habituel du compte ne fonctionne pas.")
    except smtplib.SMTPRecipientsRefused:
        return False, "Adresse du destinataire refusée par le serveur."
    except (smtplib.SMTPException, OSError) as exc:
        return False, f"Envoi impossible ({type(exc).__name__}). Vérifiez SMTP_HOST et SMTP_PORT."
    return True, "E-mail envoyé."


def reset_message(username: str, code: str, minutes: int):
    """Sujet, version texte et version HTML de l'e-mail de réinitialisation."""
    shown = f"{code[:3]} {code[3:]}"
    subject = f"{APP_NAME} — votre code de réinitialisation"
    text = (f"Bonjour {username},\n\n"
            f"Voici votre code pour choisir un nouveau mot de passe : {shown}\n\n"
            f"Il est valable {minutes} minutes et ne peut servir qu'une fois.\n"
            "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : votre mot de passe reste inchangé.\n\n"
            f"— {APP_NAME}")
    u = _html.escape(username)
    html = f"""<!doctype html><html lang="fr"><body style="margin:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:12px;overflow:hidden">
<tr><td style="background:#0b1020;color:#ffffff;padding:18px 26px;font-size:18px;font-weight:bold;border-bottom:4px solid #c6f432">{APP_NAME}</td></tr>
<tr><td style="padding:26px">
<p style="margin:0 0 14px;font-size:15px">Bonjour {u},</p>
<p style="margin:0 0 18px;font-size:15px;line-height:1.5">Voici votre code pour choisir un nouveau mot de passe :</p>
<p style="margin:0 0 18px;font-size:34px;font-weight:bold;letter-spacing:6px;text-align:center;background:#f1f5f9;border-radius:10px;padding:16px 8px">{shown}</p>
<p style="margin:0 0 10px;font-size:14px;line-height:1.5;color:#475569">Il est valable {minutes} minutes et ne peut servir qu'une fois.</p>
<p style="margin:0;font-size:14px;line-height:1.5;color:#475569">Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : votre mot de passe reste inchangé.</p>
</td></tr></table></td></tr></table></body></html>"""
    return subject, text, html
