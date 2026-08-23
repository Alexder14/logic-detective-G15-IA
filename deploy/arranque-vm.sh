#!/usr/bin/env bash
# =============================================================================
#  Script de arranque de la VM (startup-script de GCE)
# =============================================================================
#  Lo ejecuta Compute Engine como root la primera vez que la instancia arranca.
#  Deja la máquina lista para recibir el código: Docker instalado, Compose
#  disponible y una partición de intercambio para que el build no se quede sin
#  memoria al compilar la imagen con SWI-Prolog.
#
#  No clona el repositorio: el código lo sube desplegar-gcp.sh, porque el
#  repositorio es privado y la VM no tiene credenciales de GitHub.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl gnupg

# Docker desde el repositorio oficial: la versión de Ubuntu no trae el plugin
# de compose v2, que es el que usa docker-compose.yml.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

# 2 GB de swap. Construir la imagen del backend (SWI-Prolog + PySwip) es lo más
# pesado del despliegue y en una máquina de 2 GB puede morir por falta de RAM.
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# La zona horaria del proyecto, para que los logs de la bitácora cuadren.
timedatectl set-timezone America/Guatemala

touch /var/log/logic-detective-arranque-listo
