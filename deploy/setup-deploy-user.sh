#!/bin/bash
# ═══════════════════════════════════════════════════════════
# setup-deploy-user.sh — prepara el VPS para el CI/CD de Residuos 2184
#
# EJECUTAR EN EL VPS COMO ROOT, desde el directorio deploy/:
#   sudo bash setup-deploy-user.sh
#
# Qué hace (idempotente):
#   1. Crea el usuario `deploy-residuos` (shell /bin/bash, sin password).
#   2. Lo agrega al grupo `docker` (necesario para docker compose).
#   3. Instala el wrapper en /usr/local/bin/residuos-deploy.
#   4. Instala el drop-in sshd 13-deploy-residuos.conf y valida sshd -t.
#   5. Prepara ~/.ssh con permisos correctos.
#   6. Ajusta permisos de /home/morfeo/residuos (.env y .release.env).
#   7. Copia las credenciales de GHCR de `deploy` si faltan.
#   8. Recarga sshd.
#
# REQUISITOS PREVIOS:
#   - El directorio /home/morfeo/residuos/ con compose.yaml y .env
#     (el .env lo materializa OpenBao; ver docs/despliegue.md).
#   - La public key del CI se pega a mano en
#     /home/deploy-residuos/.ssh/authorized_keys (paso 3.5 de la guía).
# ═══════════════════════════════════════════════════════════
set -euo pipefail

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: ejecutar como root (sudo bash $0)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DEPLOY_USER="deploy-residuos"
DEPLOY_ROOT="/home/deploy-residuos"
MORFEO_ROOT="/home/morfeo"
APP_DIR="$MORFEO_ROOT/residuos"
APP_ENV="$APP_DIR/.env"
RELEASE_FILE="$APP_DIR/.release.env"

# ── 1. Usuario ──
log "1/8 Creando usuario $DEPLOY_USER (shell /bin/bash, sin password)"
if id "$DEPLOY_USER" &>/dev/null; then
  log "  usuario $DEPLOY_USER ya existe, continúo"
else
  # Shell real obligatoria: OpenSSH invoca ForceCommand con la login shell.
  # El acceso interactivo lo bloquea sshd (PermitTTY no + ForceCommand).
  useradd --system --home "$DEPLOY_ROOT" --shell /bin/bash "$DEPLOY_USER"
  mkdir -p "$DEPLOY_ROOT"
  chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_ROOT"
fi

# ── 2. Grupo docker ──
log "2/8 Agregando $DEPLOY_USER al grupo docker"
usermod -aG docker "$DEPLOY_USER"
log "  ⚠ grupo docker = privilegios equivalentes a root si se evade ForceCommand."
log "    Mitigado por: Match User + ForceCommand + restrict en authorized_keys."

# ── 3. Wrapper ──
log "3/8 Instalando wrapper en /usr/local/bin/residuos-deploy"
install -m 755 -o root -g root "$SCRIPT_DIR/residuos-deploy" /usr/local/bin/residuos-deploy

# ── 4. Drop-in sshd ──
log "4/8 Instalando 13-deploy-residuos.conf"
install -m 644 -o root -g root "$SCRIPT_DIR/13-deploy-residuos.conf" \
  /etc/ssh/sshd_config.d/13-deploy-residuos.conf
if ! sshd -t; then
  log "ERROR: sshd -t falló con el drop-in instalado. Revisar antes de recargar."
  exit 1
fi

# ── 5. ~/.ssh ──
log "5/8 Preparando ~/.ssh de $DEPLOY_USER"
mkdir -p "$DEPLOY_ROOT/.ssh"
chmod 700 "$DEPLOY_ROOT/.ssh"
touch "$DEPLOY_ROOT/.ssh/authorized_keys"
chmod 600 "$DEPLOY_ROOT/.ssh/authorized_keys"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_ROOT/.ssh"

# ── 6. Acceso al checkout de morfeo ──
log "6/8 Ajustando $APP_DIR"
if [ ! -d "$APP_DIR" ]; then
  log "  ⚠ No existe $APP_DIR — copiar compose.yaml ahí antes del primer deploy"
else
  HOME_MODE="$(stat -c %a "$MORFEO_ROOT" 2>/dev/null || echo '?')"
  OTHERS_X=$(( ${HOME_MODE: -1} & 1 ))
  if [ "$OTHERS_X" -eq 0 ]; then
    chmod o+x "$MORFEO_ROOT"
    log "  /home/morfeo sin traversal para others (modo $HOME_MODE) → chmod o+x"
  else
    log "  /home/morfeo permisos: $HOME_MODE (traversal OK)"
  fi

  MORFEO_USER="$(stat -c %U "$MORFEO_ROOT" 2>/dev/null || echo morfeo)"
  chown "$MORFEO_USER:$DEPLOY_USER" "$APP_DIR"
  chmod 775 "$APP_DIR"

  if [ -f "$APP_ENV" ]; then
    chgrp "$DEPLOY_USER" "$APP_ENV"
    chmod 640 "$APP_ENV"
    log "  .env: 640 $MORFEO_USER:$DEPLOY_USER (el deploy lee, no escribe)"
  else
    log "  ⚠ No existe $APP_ENV — sincronizar desde OpenBao antes del deploy"
  fi

  if [ ! -f "$RELEASE_FILE" ]; then
    install -m 664 -o "$DEPLOY_USER" -g "$DEPLOY_USER" /dev/null "$RELEASE_FILE"
  fi
  chown "$DEPLOY_USER:$DEPLOY_USER" "$RELEASE_FILE"
  chmod 664 "$RELEASE_FILE"
  log "  .release.env: 664 $DEPLOY_USER:$DEPLOY_USER"
fi

# ── 7. Credenciales de GHCR ──
# La llave del CI no se copia de otros usuarios: cada app tiene la suya
# (least privilege). Se agrega a mano en authorized_keys.
log "7/8 Credenciales de GHCR para $DEPLOY_USER"
DOCKER_CFG_SRC="/home/deploy/.docker/config.json"
DOCKER_CFG_DST="$DEPLOY_ROOT/.docker/config.json"
if [ -s "$DOCKER_CFG_DST" ]; then
  log "  docker config de $DEPLOY_USER ya existe, no se toca"
elif [ -s "$DOCKER_CFG_SRC" ]; then
  install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_ROOT/.docker"
  install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DOCKER_CFG_SRC" "$DOCKER_CFG_DST"
  log "  credenciales GHCR copiadas desde $DOCKER_CFG_SRC"
else
  log "  ⚠ Sin credenciales GHCR: si la imagen no es pública, autenticar una vez"
  log "    como $DEPLOY_USER con 'docker login ghcr.io'"
fi

if [ -s "$DEPLOY_ROOT/.ssh/authorized_keys" ]; then
  log "  authorized_keys ya tiene una llave"
else
  log "  ⚠ Pegar la public key del CI en $DEPLOY_ROOT/.ssh/authorized_keys"
fi

# AllowUsers en el hardening global puede excluir al usuario nuevo.
ALLOW_FILES="/etc/ssh/sshd_config"
for f in /etc/ssh/sshd_config.d/*.conf; do [ -f "$f" ] && ALLOW_FILES="$ALLOW_FILES $f"; done
if grep -qsE '^[[:space:]]*AllowUsers' $ALLOW_FILES; then
  if grep -hsE '^[[:space:]]*AllowUsers' $ALLOW_FILES | grep -qw "$DEPLOY_USER"; then
    log "  AllowUsers incluye $DEPLOY_USER"
  else
    log "  ⚠ $DEPLOY_USER NO está en AllowUsers: sshd rechazará el login."
    log "    Agregarlo (13-deploy-residuos.conf ya lo declara) y recargar sshd."
  fi
fi

# ── 8. Recargar sshd ──
log "8/8 Recargando sshd"
if systemctl reload ssh 2>/dev/null || systemctl restart ssh 2>/dev/null; then
  log "  sshd recargado (servicio ssh)"
elif systemctl reload sshd 2>/dev/null || systemctl restart sshd 2>/dev/null; then
  log "  sshd recargado (servicio sshd)"
else
  log "  ⚠ No se pudo recargar sshd — hacerlo a mano: sudo systemctl reload ssh"
fi

log ""
log "═══════════════════════════════════════════════════════════"
log "✅ Setup completado. PENDIENTES:"
log "  1. Public key del CI en $DEPLOY_ROOT/.ssh/authorized_keys (si no está)"
log "  2. Secrets en GitHub: VPS_HOST, VPS_SSH_PORT, VPS_DEPLOY_SSH_KEY"
log "  3. Primer deploy: residuos-deploy sha-xxxxxxx (o push de un tag vX.Y.Z)"
log "═══════════════════════════════════════════════════════════"
