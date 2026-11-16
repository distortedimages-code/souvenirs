# Souvenirs — génération des décors

Ce dépôt génère les décors du jeu avec l'API Images d'OpenAI, directement sur les serveurs de GitHub. La clé reste un secret GitHub, lue uniquement par l'étape de génération. Les personnages, eux, sont dessinés à part, en pixel art, dans le moteur du jeu.

## Une seule fois : la clé OpenAI

Sur iPhone, dans Safari, ouvrez le dépôt sur github.com :

1. **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret**.
3. Nom : `OPENAI_API_KEY`. Valeur : votre clé OpenAI. Puis **Add secret**.

## Lancer une génération

1. Onglet **Actions** → **Images** → **Run workflow**.
2. Laissez **Simulation** cochée pour un premier essai gratuit : rien n'est envoyé à OpenAI, rien n'est enregistré, le résumé indique le coût estimé.
3. Pour la vraie génération, décochez **Simulation**. Le champ **souvenir** limite à un souvenir (`s01`), **refaire** régénère une image précise (`s01/fond`).
4. Les images arrivent dans `images/generees/`, enregistrées par le workflow lui-même. Le coût de chaque lancement s'affiche dans son résumé, et le total dans `images/etat.json`.

Une image n'est régénérée que si elle manque, si son prompt a changé, ou si on la demande dans **refaire**. Le **plafond** bloque tout lancement qui ferait dépasser la dépense totale.

## Organisation

- `images/plan.json` : la liste des images, dans l'ordre (une image peut servir de référence aux suivantes).
- `images/style_commun.txt` : le style partagé par tout le jeu.
- `images/prompt_negatif.txt` : ce qu'on ne veut jamais voir.
- `images/prompts/s01/…` : un fichier par image, rangés par souvenir.
- Les calques de premier plan sont générés sur un fond magenta uni, retiré ensuite pour obtenir la transparence.
