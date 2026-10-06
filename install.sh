#!/bin/bash
# Installe l'outil de recherche de vols Duffel sur un Mac.
# Usage : curl -fsSL https://raw.githubusercontent.com/pdepre/duffel-vols/main/install.sh | bash
set -e

REPO="https://raw.githubusercontent.com/pdepre/duffel-vols/main"
DIR="$HOME/duffel-vols"

echo ""
echo "=== Installation de l'outil Vols dans $DIR ==="
mkdir -p "$DIR"
cd "$DIR"

echo "-> Telechargement des fichiers"
curl -fsSL "$REPO/app.py" -o app.py
curl -fsSL "$REPO/requirements.txt" -o requirements.txt
curl -fsSL "$REPO/Lancer-Vols.command" -o Lancer-Vols.command
chmod +x Lancer-Vols.command

echo "-> Environnement Python"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 introuvable. Installe-le (xcode-select --install ou https://python.org) puis relance."
  exit 1
fi
python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

if [ ! -s .duffel_token ]; then
  echo ""
  echo "Colle ton token Duffel (commence par duffel_live_) puis Entree :"
  read -r TOKEN < /dev/tty
  printf '%s' "$TOKEN" > .duffel_token
  chmod 600 .duffel_token
fi

ln -sf "$DIR/Lancer-Vols.command" "$HOME/Desktop/Vols.command"
xattr -d com.apple.quarantine "$DIR/Lancer-Vols.command" 2>/dev/null || true

echo ""
echo "=== Termine ==="
echo "Double-clique sur 'Vols.command' sur ton bureau pour lancer l'outil."
echo "(Premiere fois : si macOS bloque, Reglages > Confidentialite et securite > Ouvrir quand meme)"
