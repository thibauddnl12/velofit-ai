# VeloFit AI Studio — analyse posturale, comptes, essai gratuit et abonnement

## Fichiers
- `app.py` : l'application Streamlit (point d'entrée) : création du profil, analyse, résultats
- `velofit_core.py` : analyse posturale, vidéo, réglages du vélo, rapports
- `bike3d.py` : vélo 3D orientable qui montre les réglages à faire (aucune bibliothèque externe)
- `ui_kit.py` : feuille de style et composants visuels
- `accounts.py` : comptes, mots de passe hachés, codes de réinitialisation, quotas, abonnements, paiements Stripe
- `auth_ui.py` : connexion, mot de passe oublié, abonnement et administration
- `mailer.py` : envoi des e-mails (SMTP)
- `requirements.txt`, `packages.txt`, `secrets.toml.example`, `.gitignore`, `.streamlit/config.toml`

Tous les fichiers `.py` doivent être dans le même dossier que `app.py`.

## Premier lancement (local)
1. `pip install -r requirements.txt`
2. Créez `.streamlit/secrets.toml` à côté de `app.py` (modèle : `secrets.toml.example`) avec `ADMIN_USERNAME`, `ADMIN_PASSWORD` et, si possible, `ADMIN_EMAIL`.
3. `streamlit run app.py`, puis connectez-vous avec ces identifiants : l'onglet **Administration** apparaît.

## Parcours d'un utilisateur
1. **Profil** : au premier accès, le type de vélo, l'objectif, la taille, le poids, l'entrejambe, la largeur d'épaules, la souplesse et les douleurs sont demandés avant toute analyse. Tout reste modifiable dans l'onglet « Mon profil ».
2. **Photo ou vidéo** de profil.
3. **Résultats** : résumé (score, « par où commencer », vélo 3D avec les réglages numérotés, six angles), puis rubriques de détail.

## Sur quoi reposent les mesures
- Les angles visés sont rattachés à des études publiées quand il en existe (genou : 25–35° de flexion en photo posée, 30–40° en pédalant ; tronc ; hanche F.I.S.T. sur prolongateurs), sinon à des repères de bike-fitters, signalés comme tels. Le détail et les références sont dans l'onglet « Guide » et à la fin du rapport PDF.
- Disciplines : Route / Endurance, Compétition / Course, Gravel, VTT / XC, Contre-la-montre (prolongateurs), Triathlon (prolongateurs). Sur prolongateurs, la photo se prend en position de course et les conseils portent sur les accoudoirs.
- La mesure par analyse d'image a une précision d'environ ± 5° par angle : l'outil aide à régler, il ne remplace pas une étude posturale en cabinet.

## Fonctionnement
- Chaque compte reçoit N analyses gratuites (réglable, 3 par défaut). Une analyse = un fichier photo ou vidéo ; réafficher le même fichier ne coûte rien.
- Ensuite : une offre payante, au choix de l'administrateur (Administration > « Offres et tarifs ») : un accès pour un nombre de jours libre (30, 365…), un accès illimité sans date de fin payé une fois, ou les deux. Le prix affiché est libre.
- L'administrateur crée des comptes, ajoute des analyses, active/retire un abonnement, réinitialise un mot de passe, désactive ou supprime un compte, et peut fermer l'inscription libre.
- Les profils, historiques et images de chaque compte sont isolés les uns des autres.

## Mot de passe oublié (e-mail)
L'onglet « Mot de passe oublié » de la page de connexion envoie un code à 6 chiffres à l'adresse du compte (valable 15 minutes, 5 essais, 3 codes par heure au maximum). L'adresse e-mail est demandée à l'inscription ; un compte plus ancien peut l'ajouter dans la barre latérale (« E-mail et mot de passe »), ou l'administrateur dans « Gérer un compte ».

L'envoi passe par SMTP, avec n'importe quelle boîte e-mail. Ajoutez dans les secrets :
```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"                      # 587 (STARTTLS) ou 465 (SSL)
SMTP_USER = "votre.adresse@gmail.com"
SMTP_PASSWORD = "mot de passe d'application"
# SMTP_FROM = "votre.adresse@gmail.com"   # facultatif
```
Avec **Gmail** : activez la validation en deux étapes, puis créez un « mot de passe d'application » sur `myaccount.google.com/apppasswords` (le mot de passe habituel est refusé). Ce mot de passe d'application est révoqué si vous changez le mot de passe du compte Google : il faut alors en recréer un. Limite : environ 500 e-mails par jour.

Le compte administrateur défini dans les secrets fait exception : son mot de passe est celui de `ADMIN_PASSWORD`, réappliqué à chaque démarrage. Pour le changer durablement, modifiez le secret.

Vérifiez ensuite l'envoi dans Administration > « E-mails (mot de passe oublié) » > « Envoyer le test ». Tant que l'envoi n'est pas configuré, seul l'administrateur peut réinitialiser un mot de passe.

## Paiement Stripe (sans serveur de webhook)
1. Compte Stripe en **mode test** → Payment Links → lien de **paiement unique** → collez-le dans Administration > Réglages.
2. Ajoutez `STRIPE_SECRET_KEY = "sk_test_..."` dans les secrets.
3. L'utilisateur paie via le bouton « S'abonner » (son identifiant est transmis à Stripe), puis clique sur « J'ai payé » : l'application interroge Stripe et prolonge l'abonnement. Chaque paiement n'est compté qu'une fois.
4. Offre illimitée : créez un second Payment Link (paiement unique) et collez-le dans « Offre 2 », avec son identifiant `plink_...` (visible dans l'adresse de la page du lien dans Stripe) : il sert à rattacher chaque paiement à la bonne offre.
5. Testez avec la carte `4242 4242 4242 4242`, puis passez en mode réel (`sk_live_...`).
Sans clé Stripe, vous pouvez activer les abonnements à la main dans l'onglet Administration.

## Hébergement : où sont stockées les données ?
Les comptes sont dans `velofit_data/accounts.db` (SQLite). Sur **Streamlit Community Cloud**, le disque est **éphémère** : comptes, abonnements et historiques sont perdus à chaque redémarrage ou redéploiement. Pour un vrai service payant, hébergez l'application là où un disque persistant est disponible (VPS, Render/Railway/Fly.io avec volume) et pointez la variable d'environnement `VELOFIT_DATA` vers ce volume. Sinon, utilisez la version Cloud uniquement pour une démonstration.

## Mise en ligne
### A. Démonstration gratuite : Streamlit Community Cloud
1. Poussez les fichiers sur un dépôt GitHub (`.gitignore` exclut secrets et données).
2. share.streamlit.io > « Create app » > choisissez le dépôt et `app.py`. « Advanced settings » : Python 3.11 ou 3.12, puis collez les secrets (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`, `SMTP_...`, `STRIPE_SECRET_KEY`).
3. Le disque est éphémère : téléchargez régulièrement la sauvegarde (Administration > Sauvegarde) et restaurez-la après un redémarrage.

### B. Service réel avec abonnements : Render (disque persistant)
1. Dépôt GitHub comme ci-dessus (ajoutez `render.yaml`).
2. render.com > New > Blueprint > choisissez le dépôt. Renseignez `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`, les `SMTP_...` et `STRIPE_SECRET_KEY`.
3. Le disque `/var/data` conserve comptes, historiques et images (variable `VELOFIT_DATA`).

### Avant d'ouvrir au public
- Mentions légales, CGV, politique de confidentialité (photos de personnes), TVA.
- Stripe testé en mode test, puis passage en mode réel.
- Mot de passe administrateur long et unique.
