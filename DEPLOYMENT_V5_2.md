# RE-ZERO V5.2 — déploiement propre

## Important
Le correctif V5.2 élimine l'import problématique `EXECUTION_TIMEFRAMES` depuis `config.py` dans `app.py` : l'application le charge directement depuis `timeframe_policy.py`.

## GitHub / Streamlit
1. Décompresser `RE-ZERO_V5_2_IMPORT_FIXED.zip`.
2. Remplacer **tous les fichiers Python du dépôt RE-ZERO** par ceux du ZIP. Ne pas seulement remplacer `app.py`.
3. Vérifier que `app.py`, `config.py`, `timeframe_policy.py`, `version_info.py` et les autres modules sont au même niveau à la racine du dépôt.
4. Ne pas mélanger avec un ancien ZIP RE-ZERO.
5. Redéployer / relancer l'application Streamlit.
6. Dans la barre latérale, la version doit afficher `RE-ZERO V5.2`.

## Ne pas faire
- Ne pas téléverser le ZIP comme unique fichier en espérant que Streamlit l'exécute.
- Ne pas conserver un ancien `config.py` avec le nouvel `app.py`.
- Ne pas modifier le dépôt SHO-pred.

## Dépendances
Streamlit Cloud installe les dépendances depuis `requirements.txt`.

## Notifications
Les notifications navigateur nécessitent HTTPS et l'autorisation Android/navigateur. Le canal Telegram est disponible via `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` dans les secrets Streamlit. Pour une notification garantie lorsque la page est complètement fermée, un vrai Web Push avec service worker + backend/VAPID est nécessaire.
