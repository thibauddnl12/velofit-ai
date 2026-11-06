# VeloFit AI Studio — comptes, essai gratuit et abonnement

## Fichiers
- `app.py` : l'application Streamlit (point d'entrée)
- `velofit_core.py` : analyse posturale, vidéo, rapports
- `accounts.py` : comptes, mots de passe hachés, quotas, abonnements, paiements Stripe
- `auth_ui.py` : pages de connexion, abonnement et administration
- `requirements.txt`, `secrets.toml.example`, `.gitignore`

## Premier lancement (local)
1. `pip install -r requirements.txt`
2. Créez `.streamlit/secrets.toml` à côté de `app.py` (modèle : `secrets.toml.example`) avec `ADMIN_USERNAME` et `ADMIN_PASSWORD`.
3. `streamlit run app.py`, puis connectez-vous avec ces identifiants : l'onglet **🛠️ Administration** apparaît.

## Fonctionnement
- Chaque compte reçoit N analyses gratuites (réglable, 3 par défaut). Une analyse = un fichier photo ou vidéo ; réafficher le même fichier ne coûte rien.
- Ensuite : abonnement. Un paiement = X jours d'accès illimité (réglable, 30 par défaut).
- L'administrateur crée des comptes, ajoute des analyses, active/retire un abonnement, réinitialise un mot de passe, désactive ou supprime un compte, et peut fermer l'inscription libre.
- Les profils, historiques et images de chaque compte sont isolés les uns des autres.

## Paiement Stripe (sans serveur de webhook)
1. Compte Stripe en **mode test** → Payment Links → lien de **paiement unique** → collez-le dans Administration > Réglages.
2. Ajoutez `STRIPE_SECRET_KEY = "sk_test_..."` dans les secrets.
3. L'utilisateur paie via le bouton « S'abonner » (son identifiant est transmis à Stripe), puis clique sur « J'ai payé » : l'application interroge Stripe et prolonge l'abonnement. Chaque paiement n'est compté qu'une fois.
4. Testez avec la carte `4242 4242 4242 4242`, puis passez en mode réel (`sk_live_...`).
Sans clé Stripe, vous pouvez activer les abonnements à la main dans l'onglet Administration.

## ⚠️ Hébergement : où sont stockées les données ?
Les comptes sont dans `velofit_data/accounts.db` (SQLite). Sur **Streamlit Community Cloud**, le disque est **éphémère** : comptes, abonnements et historiques sont perdus à chaque redémarrage ou redéploiement. Pour un vrai service payant, hébergez l'application là où un disque persistant est disponible (VPS, Render/Railway/Fly.io avec volume) et pointez la variable d'environnement `VELOFIT_DATA` vers ce volume. Sinon, utilisez la version Cloud uniquement pour une démonstration.
