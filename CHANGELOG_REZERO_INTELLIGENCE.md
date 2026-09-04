# RE-ZERO Intelligence Core

## Corrections
- **Validation statistique**: séquentiel walk-forward, bootstrap 95%, permutation test, métriques Sharpe/Sortino, expectancy, profit factor, drawdown et diagnostic par régime.
- **Robustesse hors échantillon**: aucune ligne future n'est utilisée pour le test courant; la validation séquentielle est séparée de l'analyse actuelle.
- **Surajustement**: le rapport applique une pénalisation conservatrice du nombre d'essais et affiche un verdict de robustesse plutôt qu'un taux de réussite promis.
- **Régimes**: classification past-only TENDANCE / RANGE / TRANSITION avec COMPRESSION / NORMALE / EXPANSION de volatilité.
- **Qualité des données**: audit des colonnes, NaN, OHLC incohérent, doublons, gaps et présence du volume. Les défauts réduisent ou bloquent la qualité.
- **Décision**: nouveau garde-fou hiérarchique. La direction est un scénario conditionnel, jamais une prédiction certaine.
- **Confiance**: l'interface parle désormais de **qualité du scénario**, pas de probabilité de gain.
- **Multi-confluence**: le régime et la qualité des données sont intégrés aux barrières avant setup.

## Limites
La validation statistique ne transforme pas RE-ZERO en oracle. Elle sert à falsifier les stratégies fragiles et à éviter de confondre un beau backtest avec une preuve de robustesse. Les données Yahoo Finance peuvent être incomplètes ou différentes des données/exécutions d'un broker réel.
