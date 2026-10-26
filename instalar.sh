#!/bin/sh
# Instala o widget no usuario atual e cria o atalho "Apuração 2026" no menu de aplicativos.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
install -m 755 "$DIR/widget-eleicoes.py" "$HOME/.local/bin/widget-eleicoes.py"
cat > "$HOME/.local/share/applications/widget-eleicoes.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Apuração 2026
Comment=Widget da apuração do 2º turno (TSE)
Exec=$HOME/.local/bin/widget-eleicoes.py
Icon=x-office-presentation
Terminal=false
Categories=Utility;
EOF
echo "Pronto! Procure \"Apuração 2026\" no menu de aplicativos."
