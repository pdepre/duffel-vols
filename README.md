# duffel-vols

App web locale qui compare toutes les combinaisons de dates d'un aller-retour via l'API Duffel (vrais prix, mode Live).

## Installation sur un Mac (une ligne)

    curl -fsSL https://raw.githubusercontent.com/pdepre/duffel-vols/main/install.sh | bash

L'installeur cree `~/duffel-vols`, installe Python/venv/dependances, demande le token Duffel une seule fois (stocke dans `~/duffel-vols/.duffel_token`, jamais dans le repo) et depose `Vols.command` sur le bureau.

## Utilisation

Double-clic sur `Vols.command` : l'app demarre et le navigateur s'ouvre sur http://localhost:5001. Fermer la fenetre Terminal arrete l'app.

## Mise a jour

Relancer la meme ligne `curl` : les fichiers sont remplaces, le token est conserve.

## Notes

- Delai de 10 s entre requetes + retry automatique sur les erreurs 429 (rate limit Duffel Live).
- Un token `duffel_test_` renvoie des donnees fictives (Duffel Airways) : utiliser un token Live.
