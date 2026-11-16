# ==============================================================================
#  auth_ui.py — connexion, mot de passe oublié, abonnement et administration (Streamlit)
# ==============================================================================
from __future__ import annotations

import os
import re
import secrets

import pandas as pd
import streamlit as st

import accounts as acc
import mailer
import ui_kit


# ------------------------------------------------------------------------------
#  SECRETS ET OUTILS
# ------------------------------------------------------------------------------
def _secret(name: str, default: str = "") -> str:
    """Lit un secret : variable d'environnement d'abord, puis .streamlit/secrets.toml / secrets Streamlit Cloud."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _stretch(fn, *args, **kwargs):
    last = None
    for opt in ({"width": "stretch"}, {"use_container_width": True}, {}):
        try:
            return fn(*args, **kwargs, **opt)
        except Exception as exc:
            last = exc
    raise last


def _H(html: str):
    st.markdown(re.sub(r"\s*\n\s*", " ", html.strip()), unsafe_allow_html=True)


def _fmt_date(s):
    return s[:10] if s else "—"


@st.cache_resource(show_spinner=False)
def _bootstrap_admin(username: str, password: str, email: str = ""):
    return acc.ensure_admin(username, password, email)


def _mail_ready() -> bool:
    return mailer.is_configured(_secret)


# ------------------------------------------------------------------------------
#  CONNEXION
# ------------------------------------------------------------------------------
def _setup_help():
    _H(ui_kit.hero("Compte administrateur requis", "Aucun administrateur n'est configuré. Définissez deux secrets, puis relancez l'application.", "Configuration"))
    st.markdown("**En local**, créez le fichier `.streamlit/secrets.toml` à côté de `app.py` :")
    st.code('ADMIN_USERNAME = "votre_identifiant"\nADMIN_PASSWORD = "un-mot-de-passe-solide"\nADMIN_EMAIL = "vous@exemple.fr"\n'
            '# optionnel (paiements Stripe)\nSTRIPE_SECRET_KEY = "sk_test_..."', language="toml")
    st.markdown("**Sur Streamlit Community Cloud** : « Settings » → « Secrets », puis collez les mêmes lignes.")
    st.caption("Le mot de passe administrateur n'est jamais enregistré en clair dans la base : il est haché. Il est mis à jour à chaque démarrage si vous le changez dans les secrets.")


def _forgot_tab(cfg: dict):
    """Mot de passe oublié : un code à 6 chiffres est envoyé par e-mail, puis sert à choisir un nouveau mot de passe."""
    _H(ui_kit.form_section("1 · Recevez un code par e-mail", "Il est envoyé à l'adresse enregistrée sur votre compte.", first=True))
    with st.form("forgot_form"):
        ident = st.text_input("Identifiant ou adresse e-mail du compte", key="fg_ident")
        go = st.form_submit_button("Recevoir un code", type="primary")
    if go:
        ident = (ident or "").strip()
        if not _mail_ready():
            st.warning("L'envoi d'e-mails n'est pas encore activé sur ce site. Demandez à l'administrateur de réinitialiser votre mot de passe."
                       + (f" Contact : {cfg['contact']}" if cfg.get("contact") else ""))
        elif not ident:
            st.error("Indiquez votre identifiant ou votre adresse e-mail.")
        else:
            user, code, _why = acc.request_reset(ident)
            if user is not None:
                subject, text, html = mailer.reset_message(user["username"], code, acc.RESET_MINUTES)
                ok, msg = mailer.send(_secret, user["email"], subject, text, html)
                if not ok:
                    print(f"[VeloFit] E-mail de réinitialisation non envoyé : {msg}", flush=True)   # visible dans les journaux du serveur
            st.session_state["rs_ident"] = ident
            # même message que le compte existe ou non : on ne révèle pas qui est inscrit
            st.success(f"Si un compte correspond, un e-mail avec un code à 6 chiffres vient de partir vers l'adresse enregistrée. "
                       f"Il est valable {acc.RESET_MINUTES} minutes. Pensez à vérifier les courriers indésirables ; "
                       f"{acc.RESET_MAX_PER_HOUR} codes au maximum peuvent être demandés par heure.")
    _H(ui_kit.form_section("2 · Choisissez un nouveau mot de passe", "Saisissez le code reçu, puis votre nouveau mot de passe."))
    with st.form("reset_form"):
        ident2 = st.text_input("Identifiant ou adresse e-mail du compte", key="rs_ident")
        code = st.text_input("Code reçu par e-mail (6 chiffres)", key="rs_code")
        p1 = st.text_input("Nouveau mot de passe (8 caractères minimum)", type="password", key="rs_pw1")
        p2 = st.text_input("Confirmer le nouveau mot de passe", type="password", key="rs_pw2")
        go2 = st.form_submit_button("Changer mon mot de passe", type="primary")
    if go2:
        if p1 != p2:
            st.error("Les deux mots de passe ne correspondent pas.")
        else:
            ok, msg = acc.reset_password(ident2, code, p1)
            (st.success if ok else st.error)(msg)
    st.caption("Pas d'e-mail enregistré sur votre compte ? Demandez à l'administrateur de réinitialiser votre mot de passe.")


def _login_page():
    cfg = acc.get_settings()
    free = acc.setting_int(cfg, "free_credits")
    _H(ui_kit.hero("VeloFit AI Studio", f"Connectez-vous pour analyser votre position. Chaque nouveau compte reçoit <b>{free} analyses gratuites</b> ; au-delà, un abonnement donne un accès illimité."))
    allow = cfg["allow_signup"] == "1"
    names = ["Connexion"] + (["Créer un compte"] if allow else []) + ["Mot de passe oublié"]
    _l, _mid, _r = st.columns([1, 1.5, 1])
    with _mid:
        tabs = st.tabs(names)
    with tabs[0]:
        with st.form("login_form"):
            u = st.text_input("Identifiant", key="login_user")
            p = st.text_input("Mot de passe", type="password", key="login_pw")
            go = st.form_submit_button("Se connecter", type="primary")
        if go:
            user, msg = acc.authenticate(u, p)
            if user is None:
                st.error(msg)
            else:
                st.session_state["auth_user"] = user["username"]
                st.rerun()
        if not allow:
            st.caption("Les inscriptions sont fermées : demandez un compte à l'administrateur.")
        st.caption("Mot de passe oublié ? Ouvrez l'onglet « Mot de passe oublié » ci-dessus pour recevoir un code par e-mail.")
    if allow:
        with tabs[1]:
            with st.form("signup_form"):
                u = st.text_input("Identifiant (lettres minuscules, chiffres, _ ou -)", key="su_user")
                e = st.text_input("Adresse e-mail (pour récupérer votre mot de passe en cas d'oubli)", key="su_mail")
                p1 = st.text_input("Mot de passe (8 caractères minimum)", type="password", key="su_pw1")
                p2 = st.text_input("Confirmer le mot de passe", type="password", key="su_pw2")
                ok_rgpd = st.checkbox("J'accepte que mes photos et vidéos soient traitées pour produire l'analyse. Elles ne sont conservées que si j'enregistre l'analyse dans mon historique.", key="su_rgpd")
                go = st.form_submit_button("Créer mon compte", type="primary")
            if go:
                if p1 != p2:
                    st.error("Les deux mots de passe ne correspondent pas.")
                elif not ok_rgpd:
                    st.error("Merci d'accepter le traitement de vos images pour continuer.")
                else:
                    ok, msg = acc.create_user(u, p1, email=e, check_signup=True, require_email=True)
                    if ok:
                        st.session_state["auth_user"] = acc.clean_username(u)
                        st.rerun()
                    else:
                        st.error(msg)
    with tabs[-1]:
        _forgot_tab(cfg)


def gate():
    """Retourne l'utilisateur connecté (dict). Sinon affiche la page de connexion et arrête le script."""
    a_user, a_pw = _secret("ADMIN_USERNAME"), _secret("ADMIN_PASSWORD")
    if a_user and a_pw:
        ok, msg = _bootstrap_admin(a_user, a_pw, _secret("ADMIN_EMAIL"))
        if not ok:
            st.error(msg)
            st.stop()
    if not acc.has_admin():
        _setup_help()
        st.stop()
    name = st.session_state.get("auth_user")
    if name:
        user = acc.get_user(name)
        if user and user["active"]:
            return user
        st.session_state.pop("auth_user", None)
    _login_page()
    st.stop()


def logout():
    """Déconnexion : tout l'état de la session est effacé, pour qu'un autre compte reparte de zéro sur le même appareil."""
    for k in list(st.session_state.keys()):
        try:
            del st.session_state[k]
        except Exception:
            pass
    st.rerun()


# ------------------------------------------------------------------------------
#  ABONNEMENT
# ------------------------------------------------------------------------------
def subscribe_panel(user: dict, kp: str = "sub_"):
    """Offres proposées (durée limitée et/ou accès illimité, au choix de l'administrateur) et vérification du paiement."""
    cfg = acc.get_settings()
    offs = acc.offers(cfg)
    if acc.status(user).get("lifetime"):
        st.success("Vous avez un accès illimité, sans date de fin.")
        return
    if not offs:
        st.info("Aucune offre n'est ouverte pour le moment. Contactez l'administrateur pour activer votre accès.")
    any_link = False
    for i, o in enumerate(offs):
        st.markdown(f"**{o['name']}** — {o['price']}")
        st.caption("Analyses illimitées, sans date de fin : un seul paiement." if o["kind"] == "life"
                   else f"Analyses illimitées pendant {o['days']} jours à chaque paiement.")
        url = acc.payment_url(cfg, user["username"], user.get("email", ""), link=o["link"])
        if url:
            any_link = True
            label = "Choisir l'accès illimité" if o["kind"] == "life" else "Choisir cette offre"
            if hasattr(st, "link_button"):
                st.link_button(label, url)
            else:
                st.markdown(f"[{label}]({url})")
    if any_link:
        st.caption("Après le paiement, revenez ici et cliquez sur le bouton ci-dessous.")
        if st.button("J'ai payé : vérifier mon paiement", key=kp + "check", type="primary"):
            with st.spinner("Vérification du paiement…"):
                n, msg = acc.sync_payments(user["username"], _secret("STRIPE_SECRET_KEY"), cfg)
            (st.success if n else st.info)(msg)
            if n:
                st.rerun()
    elif offs:
        st.info("Le paiement en ligne n'est pas encore ouvert. Contactez l'administrateur pour activer votre accès.")
    if cfg["contact"]:
        st.caption(f"Une question ? {cfg['contact']}")


def paywall(user: dict):
    stt = acc.status(user)
    _H(f"""<div class="glass"><h3 style="margin:0 0 6px;">Vos {stt['free_total']} analyses gratuites sont utilisées</h3>
    <p style="color:#8b97a8;margin:0;">Choisissez une offre pour continuer à analyser vos photos et vidéos sans limite. Votre historique et vos profils restent accessibles.</p></div>""")
    st.write("")
    subscribe_panel(user, "pw_")


def sidebar_box(user: dict):
    stt = acc.status(user)
    st.markdown(f"**{user['username']}**" + ("  ·  administrateur" if stt["is_admin"] else ""))
    if stt["is_admin"]:
        st.caption("Accès illimité.")
    elif stt["lifetime"]:
        st.success("Accès illimité, sans date de fin")
    elif stt["sub_active"]:
        st.success(f"Abonnement actif jusqu'au {stt['sub_until']:%d/%m/%Y}")
    else:
        total = max(1, stt["free_total"])
        st.progress(min(1.0, stt["free_left"] / total), text=f"Analyses gratuites restantes : {stt['free_left']} / {stt['free_total']}")
    if not stt["is_admin"] and not stt["lifetime"]:
        with st.expander("Abonnement" if not stt["sub_active"] else "Prolonger ou passer en illimité"):
            subscribe_panel(user, "sb_")
    has_mail = bool(acc.clean_email(user.get("email")))
    if not has_mail:
        st.warning("Ajoutez votre e-mail ci-dessous : sans lui, impossible de récupérer votre mot de passe en cas d'oubli.")
    with st.expander("E-mail et mot de passe", expanded=not has_mail):
        with st.form("mail_form"):
            em = st.text_input("Adresse e-mail (récupération du mot de passe)", value=user.get("email") or "", key="acct_mail")
            go_mail = st.form_submit_button("Enregistrer l'e-mail")
        if go_mail:
            ok, msg = acc.set_email(user["username"], em)
            (st.success if ok else st.error)(msg)
        if acc.clean_username(_secret("ADMIN_USERNAME")) == user["username"]:
            st.caption("Ce compte administrateur est défini dans les secrets : pour changer son mot de passe durablement, modifiez "
                       "ADMIN_PASSWORD dans les secrets. Un changement fait ici (ou par e-mail) est annulé au prochain redémarrage.")
        with st.form("pw_form", clear_on_submit=True):
            old = st.text_input("Mot de passe actuel", type="password")
            new = st.text_input("Nouveau mot de passe", type="password")
            go = st.form_submit_button("Modifier le mot de passe", type="primary")
        if go:
            ok, msg = acc.change_own_password(user["username"], old, new)
            (st.success if ok else st.error)(msg)
    if st.button("Se déconnecter", key="logout_btn"):
        logout()
    st.caption("Votre analyse n'est comptée qu'une fois par fichier : la réafficher ne coûte rien.")


# ------------------------------------------------------------------------------
#  ADMINISTRATION
# ------------------------------------------------------------------------------
def _users_df(users):
    rows = []
    for u in users:
        s = acc.status(u)
        rows.append({
            "Identifiant": u["username"], "Rôle": u["role"], "Actif": "oui" if u["active"] else "non", "E-mail": u["email"],
            "Créé le": _fmt_date(u["created_at"]), "Dernière connexion": _fmt_date(u["last_login"]),
            "Gratuites": f"{s['free_used']}/{s['free_total']}", "Abonnement jusqu'au": ("illimité" if s["lifetime"] else _fmt_date(u["sub_until"])) if s["sub_active"] else "—",
            "Analyses": u["n_analyses"],
        })
    return pd.DataFrame(rows)


def admin_panel(admin: dict):
    if admin.get("role") != "admin":  # garde-fou : ne jamais afficher à un non-administrateur
        st.error("Accès réservé à l'administrateur.")
        return
    stats = acc.stats()
    c = st.columns(5)
    c[0].metric("Comptes", stats["users"])
    c[1].metric("Abonnés actifs", stats["subscribers"])
    c[2].metric("Analyses totales", stats["analyses"])
    c[3].metric("Analyses (7 jours)", stats["analyses_7d"])
    c[4].metric("Paiements", stats["payments"])

    users = acc.list_users()
    st.markdown("##### Comptes")
    df = _users_df(users)
    _stretch(st.dataframe, df, hide_index=True)
    st.download_button("Exporter les comptes (CSV)", df.to_csv(index=False).encode("utf-8"), "comptes.csv", "text/csv", key="adm_csv")

    st.markdown("##### Créer un compte")
    with st.form("adm_create", clear_on_submit=False):
        a1, a2 = st.columns(2)
        nu = a1.text_input("Identifiant", key="adm_nu")
        ne = a2.text_input("E-mail (conseillé : sert à récupérer le mot de passe)", key="adm_ne")
        npw = a1.text_input("Mot de passe (vide = générer automatiquement)", type="password", key="adm_npw")
        nrole = a2.selectbox("Rôle", ["user", "admin"], key="adm_nrole")
        ncred = a1.number_input("Analyses gratuites", 0, 1000, acc.setting_int(acc.get_settings(), "free_credits"), key="adm_ncred")
        nsub = a2.number_input("Jours d'abonnement offerts", 0, 3650, 0, key="adm_nsub")
        go = st.form_submit_button("Créer le compte", type="primary")
    if go:
        pw = npw or secrets.token_urlsafe(9)
        ok, msg = acc.create_user(nu, pw, role=nrole, free_credits=int(ncred), sub_days=int(nsub), email=ne)
        if ok:
            st.success(msg)
            if not npw:
                st.warning("Mot de passe généré — notez-le maintenant, il ne sera plus affiché :")
                st.code(pw)
        else:
            st.error(msg)

    st.markdown("##### Gérer un compte")
    names = [u["username"] for u in users]
    if names:
        sel = st.selectbox("Compte", names, key="adm_sel")
        target = acc.get_user(sel)
        stt = acc.status(target)
        is_self = target["username"] == admin["username"]
        st.caption(f"Gratuites : {stt['free_used']}/{stt['free_total']} utilisées · "
                   f"abonnement : {'illimité, sans date de fin' if stt['lifetime'] else ('jusqu’au ' + stt['sub_until'].strftime('%d/%m/%Y') if stt['sub_active'] else 'aucun')}")
        b1, b2, b3 = st.columns(3)
        n_add = b1.number_input("Ajouter des analyses gratuites", 1, 1000, 3, key="adm_addn")
        if b1.button("Ajouter", key="adm_add"):
            acc.add_credits(sel, int(n_add))
            st.rerun()
        n_days = b2.number_input("Activer / prolonger (jours)", 1, 3650, acc.setting_int(acc.get_settings(), "plan_days"), key="adm_days")
        if b2.button("Activer l'abonnement", key="adm_sub"):
            acc.set_subscription(sel, int(n_days))
            st.rerun()
        if b3.button("Donner l'accès illimité", key="adm_life", help="Analyses illimitées, sans date de fin."):
            acc.set_lifetime(sel)
            st.rerun()
        if b3.button("Retirer l'abonnement", key="adm_unsub"):
            acc.clear_subscription(sel)
            st.rerun()
        m1, m2 = st.columns(2)
        newmail = m1.text_input("Adresse e-mail de ce compte", value=target.get("email") or "", key=f"adm_mail_{sel}")
        m2.write("")
        m2.write("")
        if m2.button("Enregistrer l'e-mail", key="adm_mail_btn"):
            ok, msg = acc.set_email(sel, newmail)
            (st.success if ok else st.error)(msg)
        d1, d2 = st.columns(2)
        newpw = d1.text_input("Nouveau mot de passe pour ce compte", type="password", key="adm_resetpw")
        if d1.button("Réinitialiser le mot de passe", key="adm_reset"):
            ok, msg = acc.set_password(sel, newpw)
            (st.success if ok else st.error)(msg)
        d2.write("")
        d2.write("")
        if is_self:
            d2.caption("Vous ne pouvez ni désactiver ni supprimer votre propre compte.")
        else:
            if target["active"]:
                if d2.button("Désactiver le compte", key="adm_off"):
                    acc.set_active(sel, False)
                    st.rerun()
            else:
                if d2.button("Réactiver le compte", key="adm_on"):
                    acc.set_active(sel, True)
                    st.rerun()
            with st.expander("Supprimer ce compte"):
                st.caption("Supprime le compte, son décompte d'analyses et, si coché, ses profils et photos enregistrés. Irréversible.")
                wipe = st.checkbox("Supprimer aussi ses données (profils, historique, images)", value=True, key="adm_wipe")
                sure = st.checkbox(f"Je confirme la suppression de « {sel} »", key="adm_sure")
                if st.button("Supprimer définitivement", key="adm_del", disabled=not sure):
                    acc.delete_user(sel, delete_data=wipe)
                    st.rerun()

    st.markdown("##### E-mails (mot de passe oublié)")
    mcfg = mailer.settings(_secret)
    no_mail = sum(1 for u in users if not acc.clean_email(u.get("email")))
    if mcfg is None:
        st.warning("L'envoi d'e-mails n'est pas configuré : les utilisateurs ne peuvent pas récupérer leur mot de passe seuls. "
                   "Ajoutez SMTP_HOST, SMTP_USER et SMTP_PASSWORD dans les secrets (voir ci-dessous).")
    else:
        st.caption(f"Envoi configuré : serveur {mcfg['host']}, port {mcfg['port']}, expéditeur {mcfg['sender']}.")
        t1, t2 = st.columns(2)
        dest = t1.text_input("Envoyer un e-mail de test à", value=admin.get("email") or "", key="adm_test_to")
        t2.write("")
        t2.write("")
        if t2.button("Envoyer le test", key="adm_test_btn"):
            if acc.check_email(acc.clean_email(dest)):
                st.error("Adresse e-mail invalide.")
            else:
                with st.spinner("Envoi…"):
                    ok, msg = mailer.send(_secret, acc.clean_email(dest), "VeloFit AI Studio — e-mail de test",
                                          "Ceci est un e-mail de test : l'envoi fonctionne, la récupération du mot de passe est active.")
                (st.success if ok else st.error)(msg + (" Vérifiez la boîte de réception (et les indésirables)." if ok else ""))
    if no_mail:
        st.caption(f"{no_mail} compte(s) sans adresse e-mail : ils ne pourront pas recevoir de code. Vous pouvez saisir leur adresse dans « Gérer un compte ».")
    with st.expander("Comment activer l'envoi d'e-mails ?"):
        st.markdown(
            "L'application envoie les codes par SMTP, avec n'importe quelle boîte e-mail. Exemple avec **Gmail** :\n"
            "1. Sur votre compte Google, activez la **validation en deux étapes** (Sécurité).\n"
            "2. Ouvrez `myaccount.google.com/apppasswords`, créez un **mot de passe d'application** (16 lettres).\n"
            "3. Dans les secrets (Streamlit Cloud : « Settings » → « Secrets »), ajoutez :")
        st.code('SMTP_HOST = "smtp.gmail.com"\nSMTP_PORT = "587"\nSMTP_USER = "votre.adresse@gmail.com"\nSMTP_PASSWORD = "le mot de passe d\'application"\n'
                '# facultatif : adresse affichée comme expéditeur\n# SMTP_FROM = "votre.adresse@gmail.com"', language="toml")
        st.markdown("4. Enregistrez, relancez l'application, puis utilisez « Envoyer le test » ci-dessus.\n\n"
                    "Le mot de passe habituel de la boîte ne fonctionne pas avec Gmail : il faut le mot de passe d'application. "
                    "Avec un autre fournisseur, utilisez son serveur SMTP (port 587 ou 465).")

    st.markdown("##### Offres et tarifs")
    st.caption("Vous choisissez la formule : un accès pour un nombre de jours de votre choix (30 pour un mois, 365 pour un an…), "
               "un accès illimité sans date de fin payé une seule fois, ou les deux. Le prix affiché est libre.")
    cfg = acc.get_settings()
    with st.form("adm_settings"):
        s1, s2 = st.columns(2)
        fc = s1.number_input("Analyses gratuites pour les nouveaux comptes", 0, 1000, acc.setting_int(cfg, "free_credits"), key="adm_fc")
        allow = s2.checkbox("Autoriser l'inscription libre", value=cfg["allow_signup"] == "1", key="adm_allow")
        ct = st.text_input("Contact affiché aux utilisateurs", value=cfg["contact"], key="adm_ct", placeholder="vous@exemple.fr")
        st.markdown("**Offre 1 · Accès à durée limitée**")
        pe = st.checkbox("Proposer cette offre", value=cfg["plan_enabled"] == "1", key="adm_pe")
        s1, s2, s3 = st.columns(3)
        pn = s1.text_input("Nom de l'offre", value=cfg["plan_name"], key="adm_pn")
        pp = s2.text_input("Prix affiché", value=cfg["plan_price"], key="adm_pp")
        pd_ = s3.number_input("Jours d'accès par paiement", 1, 3650, acc.setting_int(cfg, "plan_days"), key="adm_pd")
        pl = st.text_input("Lien de paiement Stripe de l'offre 1 (Payment Link, paiement unique)", value=cfg["payment_link"], key="adm_pl", placeholder="https://buy.stripe.com/...")
        pid = st.text_input("Identifiant du lien de l'offre 1 (plink_..., facultatif)", value=cfg["stripe_link_id"], key="adm_pid")
        st.markdown("**Offre 2 · Accès illimité, sans date de fin**")
        le = st.checkbox("Proposer cette offre", value=cfg["life_enabled"] == "1", key="adm_le")
        s1, s2 = st.columns(2)
        ln = s1.text_input("Nom de l'offre illimitée", value=cfg["life_name"], key="adm_ln")
        lp = s2.text_input("Prix affiché de l'offre illimitée", value=cfg["life_price"], key="adm_lp")
        ll = st.text_input("Lien de paiement Stripe de l'offre 2 (Payment Link, paiement unique)", value=cfg["life_link"], key="adm_ll", placeholder="https://buy.stripe.com/...")
        lid = st.text_input("Identifiant du lien de l'offre 2 (plink_...)", value=cfg["life_link_id"], key="adm_lid",
                            help="Obligatoire si les deux offres ont un lien de paiement : il permet de savoir quelle offre a été payée.")
        go = st.form_submit_button("Enregistrer les réglages", type="primary")
    if go:
        pl, ll, pid, lid = pl.strip(), ll.strip(), pid.strip(), lid.strip()
        if any(x and not x.startswith("https://") for x in (pl, ll)):
            st.error("Un lien de paiement doit commencer par https://")
        elif any(x and not x.startswith("plink_") for x in (pid, lid)):
            st.error("Un identifiant de lien commence par plink_ (il se trouve dans l'adresse de la page du lien, dans Stripe).")
        elif pe and le and pl and ll and not lid:
            st.error("Les deux offres ont un lien de paiement : renseignez l'identifiant (plink_...) du lien de l'offre illimitée, "
                     "sinon un paiement ne peut pas être rattaché à la bonne offre.")
        elif pe and le and pl and ll and (pl == ll or (pid and pid == lid)):
            st.error("Les deux offres doivent avoir chacune leur propre lien de paiement.")
        elif (pe and not pn.strip()) or (le and not ln.strip()):
            st.error("Donnez un nom à chaque offre proposée.")
        else:
            for k, v in (("free_credits", int(fc)), ("allow_signup", "1" if allow else "0"), ("contact", ct.strip()),
                         ("plan_enabled", "1" if pe else "0"), ("plan_name", pn.strip()), ("plan_price", pp.strip()), ("plan_days", int(pd_)),
                         ("payment_link", pl), ("stripe_link_id", pid),
                         ("life_enabled", "1" if le else "0"), ("life_name", ln.strip()), ("life_price", lp.strip()), ("life_link", ll), ("life_link_id", lid)):
                acc.set_setting(k, v)
            st.success("Réglages enregistrés. Le nombre d'analyses gratuites ne s'applique qu'aux nouveaux comptes.")
            st.rerun()
    key = _secret("STRIPE_SECRET_KEY")
    st.caption("Clé secrète Stripe : " + (f"configurée ({key[:7]}…)" if key else "absente (vérification automatique des paiements désactivée ; vous pouvez activer les abonnements à la main ci-dessus)."))
    with st.expander("Comment brancher Stripe ?"):
        st.markdown(
            "1. Créez un compte sur stripe.com et restez d'abord en **mode test**.\n"
            "2. « Payment Links » → créez un lien pour un **paiement unique** (pas un abonnement récurrent) au prix de votre offre. Copiez le lien ici.\n"
            "3. Ajoutez la clé secrète (`sk_test_...`) dans les secrets : `STRIPE_SECRET_KEY`.\n"
            "4. Testez avec la carte `4242 4242 4242 4242` : après le paiement, l'utilisateur clique sur « J'ai payé » et son abonnement est prolongé.\n"
            "5. Passez ensuite en mode réel avec le lien et la clé `sk_live_...`.\n\n"
            "Offre à durée limitée : chaque paiement donne le nombre de jours réglé ci-dessus ; l'utilisateur rachète pour renouveler. "
            "Offre illimitée : créez un second lien de paiement unique, au prix voulu ; son identifiant `plink_...` se lit dans l'adresse de la page du lien dans Stripe. "
            "Un prélèvement automatique chaque mois demanderait un petit serveur de webhooks (non inclus).")

    pays = acc.list_payments()
    if pays:
        st.markdown("##### Paiements reçus")
        pdf = pd.DataFrame([{"Date": p["ts"][:16].replace("T", " "), "Compte": p["username"],
                             "Montant": f"{p['amount'] / 100:.2f} {str(p['currency'] or '').upper()}" if p["amount"] is not None else "—", "Accès": "illimité" if p["days"] == acc.LIFETIME_DAYS else f"{p['days']} jours"} for p in pays])
        _stretch(st.dataframe, pdf, hide_index=True)

    with st.expander("Sauvegarde et restauration des comptes"):
        st.caption("Téléchargez régulièrement une sauvegarde : si votre hébergement efface le disque, vous pourrez restaurer vos comptes, abonnements et réglages. "
                   "Les photos et historiques des utilisateurs ne sont pas inclus.")
        st.download_button("Télécharger la sauvegarde", acc.backup_bytes(), "velofit_comptes.db", "application/octet-stream", key="adm_backup")
        up = st.file_uploader("Restaurer depuis une sauvegarde (.db)", type=["db"], key="adm_restore_file")
        if up is not None:
            sure = st.checkbox("Je confirme : cela remplace tous les comptes actuels.", key="adm_restore_ok")
            if st.button("Restaurer", key="adm_restore_btn", disabled=not sure):
                ok, msg = acc.restore_from_bytes(up.getvalue())
                (st.success if ok else st.error)(msg)
                if ok:
                    st.session_state.pop("auth_user", None)
                    st.info("Reconnectez-vous pour continuer.")
