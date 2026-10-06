#!/bin/bash
# Lance l'app et ouvre le navigateur. Fermer cette fenetre arrete l'app.
cd "$(dirname "$(readlink "$0" || echo "$0")")"
source venv/bin/activate
export DUFFEL_TOKEN=$(cat .duffel_token)
(sleep 2 && open "http://localhost:5001") &
python3 app.py
