# Despliegue en el VPS

El proyecto se despliega siguiendo el patrón de
[`VPS-Infrastructure`](https://github.com/ariel-david-collab/vps-infrastructure):
Traefik termina TLS, la app se consume como imagen de GHCR, los `.env` los
materializa **OpenBao** y el CI entra por SSH con un usuario `ForceCommand`.

```
Internet → Traefik :443 (ACME) → red 'web' → residuos-2184:8000
                                                   │
                                          FastAPI + WASM en la misma imagen
```

No hay base de datos, login ni credenciales de aplicación. El contenedor **no
publica puertos**: solo lo alcanza Traefik por la red `web`.

## 1. Archivos de despliegue

| Archivo | Rol |
|---|---|
| `deploy/compose.yaml` | Compose de producción: imagen pineada por `.release.env`, labels de Traefik, límites. |
| `deploy/.env.example` | Plantilla del `.env` (`DOMINIO`, `TZ`). El real lo escribe OpenBao. |
| `deploy/residuos-deploy` | Wrapper del usuario `deploy-residuos`: valida el tag, lo pinea y hace el health check. |
| `deploy/13-deploy-residuos.conf` | Drop-in de `sshd`: `ForceCommand` + sin TTY/forwarding. |
| `deploy/setup-deploy-user.sh` | Bootstrap idempotente del usuario, permisos y credenciales de GHCR. |

## 2. Qué guarda OpenBao

La app no maneja secretos, pero el patrón centraliza igual el `.env` de
despliegue en OpenBao para que el VPS sea reemplazable y no haya archivos
editados a mano:

- Path KV v2: `secret/residuos/prod`
- Campo único: `content` (contenido completo del `.env`)
- Destino: `/home/morfeo/residuos/.env` (`640`, grupo `deploy-residuos`)
- Se re-sincroniza cada 15 minutos con `openbao-secrets-sync.timer`.

Si más adelante aparece una clave real (por ejemplo, una API externa), se
agrega al mismo `.env` y viaja por el mismo camino: nunca al repositorio.

## 3. Preparar el VPS (una sola vez)

### 3.1 Inventario

Antes de tocar nada, confirmar que no se pisa el proxy ni OpenBao:

```bash
docker ps --format '{{.Names}}\t{{.Ports}}'
ss -ltnp | grep -E ':(80|443|2277|8200)\b'
docker network ls | grep -w web
```

### 3.2 Copiar los archivos

Desde la máquina local:

```powershell
scp -r "deploy" morfeo@<VPS>:/home/morfeo/deploy-residuos
```

En el VPS:

```bash
sudo install -d -m 775 -o morfeo -g morfeo /home/morfeo/residuos
install -m 644 /home/morfeo/deploy-residuos/compose.yaml /home/morfeo/residuos/compose.yaml
sudo bash /home/morfeo/deploy-residuos/setup-deploy-user.sh
```

El script crea `deploy-residuos`, instala el wrapper y el drop-in, valida
`sshd -t` y recarga SSH. Si `/home/deploy/.ssh/authorized_keys` tiene la llave
del CI, la copia; si no, el paso 3.5 la agrega.

### 3.3 Cargar el `.env` en OpenBao

```bash
cp /home/morfeo/deploy-residuos/.env.example /tmp/residuos.env
nano /tmp/residuos.env                 # DOMINIO real, sin https:// ni barra final
sudo bash /home/morfeo/scripts/secrets/import-env.sh residuos/prod /tmp/residuos.env
rm -f /tmp/residuos.env
```

`import-env.sh` verifica el round-trip por sha256 antes de dar OK.

### 3.4 Registrar el archivo en `apps.conf`

En `/home/morfeo/scripts/secrets/apps.conf` (una sola vez por app), con el
gid real del grupo:

```bash
GID=$(getent group deploy-residuos | cut -d: -f3)
echo "residuos/prod|/home/morfeo/residuos/.env|640|$GID" \
  | sudo tee -a /home/morfeo/scripts/secrets/apps.conf
sudo bash /home/morfeo/scripts/secrets/sync-secrets.sh
```

Verificar que el usuario de deploy puede leerlo:

```bash
sudo -u deploy-residuos test -r /home/morfeo/residuos/.env && echo "lectura OK"
```

> El mismo cambio conviene versionarlo en
> `VPS-Infrastructure/scripts/secrets/apps.conf` para que un VPS nuevo lo
> replique.

### 3.5 Llave SSH y secretos de GitHub

Generar una llave exclusiva del CI (sin passphrase):

```bash
ssh-keygen -t ed25519 -C "deploy-ci-residuos@github-actions" \
  -f "$HOME/.ssh/deploy_residuos_key" -N ""
```

Autorizarla con `restrict` (sin PTY, sin forwarding, sin user-rc):

```bash
echo "restrict $(cat "$HOME/.ssh/deploy_residuos_key.pub")" \
  | ssh morfeo@<VPS> 'sudo tee -a /home/deploy-residuos/.ssh/authorized_keys >/dev/null'
```

Cargar los secretos del repositorio:

```bash
gh secret set VPS_HOST --body "<IP o dominio del VPS>"
gh secret set VPS_SSH_PORT --body "2277"
gh secret set VPS_DEPLOY_SSH_KEY < "$HOME/.ssh/deploy_residuos_key"
```

### 3.6 Credenciales de GHCR (solo si el paquete es privado)

`setup-deploy-user.sh` copia `/home/deploy/.docker/config.json` si existe. Si
no, autenticar una vez como el usuario de deploy:

```bash
sudo -u deploy-residuos docker login ghcr.io -u <usuario>
```

## 4. Primer despliegue

El wrapper solo acepta tags `sha-xxxxxxx` o `vX.Y.Z`. El primer build de
`main` publica `sha-<commit>`; con ese tag:

```bash
sudo -u deploy-residuos env SSH_ORIGINAL_COMMAND="residuos-deploy sha-abc1234" \
  /usr/local/bin/residuos-deploy
```

El wrapper hace `docker pull`, escribe `RESIDUOS_IMAGE_TAG` en
`/home/morfeo/residuos/.release.env`, recrea el contenedor y espera hasta 96 s
a que `https://<DOMINIO>/api/health` responda.

## 5. CI/CD

| Evento | Efecto |
|---|---|
| push a `main` | Pruebas + imagen `:sha-xxxxxxx` y `:latest` en GHCR. **No despliega.** |
| push de tag `vX.Y.Z` | Build + deploy de ese tag exacto. |
| `workflow_dispatch` con `deploy_tag` | Deploy de un tag ya publicado. |
| pull request | Solo pruebas. |

El deploy entra como `deploy-residuos`; `sshd` fuerza
`/usr/local/bin/residuos-deploy` y el wrapper solo acepta dos argumentos con un
tag de la allowlist. `main` es el gate: un commit roto publica imagen pero no
llega a producción.

```bash
git tag v1.0.0 && git push origin v1.0.0   # dispara el deploy
```

## 6. Verificación

```bash
curl -fsS https://<DOMINIO>/api/health
# {"ok":true,"modelo":"modelB_improved","clases":9}

curl -fsS https://<DOMINIO>/api/catalogo | head -c 200
docker inspect -f '{{.State.Health.Status}}' residuos-2184   # healthy

echo | openssl s_client -connect <DOMINIO>:443 -servername <DOMINIO> 2>/dev/null \
  | openssl x509 -noout -issuer -dates                        # issuer = Let's Encrypt
```

En el navegador: cargar una foto y comprobar la bolsa. La cámara exige HTTPS,
así que se entra por el dominio, nunca por IP.

## 7. Actualizar y volver atrás

El tag desplegado vive en `/home/morfeo/residuos/.release.env`; un
`docker compose up -d` posterior conserva ese tag. No se edita a mano: lo
escribe el wrapper.

Rollback = desplegar de nuevo un tag anterior que siga en GHCR:

```bash
sudo -u deploy-residuos env SSH_ORIGINAL_COMMAND="residuos-deploy sha-<anterior>" \
  /usr/local/bin/residuos-deploy
```

No usar `docker compose restart` después de cambiar el `.env`: no re-inyecta
variables. Usar `docker compose up -d` (o el wrapper).

## 8. Escaneo de secretos (gitleaks)

`.github/workflows/secret-scan.yml` corre gitleaks v8.30.1 sobre el rango del
push o del pull request, con `--redact`. Es el mismo job del workflow
reutilizable `ariel-david-collab/ci-workflows`, pero **inline**: GitHub no
permite que un repositorio público llame a un workflow reutilizable que vive en
un repositorio privado. Si el repo pasara a privado, se puede volver al caller
de 6 líneas.

El repo es público, así que además tiene secret scanning y push protection de
GitHub gratis.

## 9. Notas de seguridad

- `deploy-residuos` pertenece al grupo `docker`: privilegios equivalentes a
  root si se evade `ForceCommand`. Hay tres capas: `Match User` +
  `ForceCommand` + `restrict` en `authorized_keys`.
- El puerto SSH actual del VPS es `2277`. Cuando se cierre a Internet (fin de
  la migración a Tailscale de las otras apps), el job de deploy debe pasar a
  un nodo efímero de Tailscale, como en `openlabs-console`. Es un cambio de
  seis líneas en el workflow; el wrapper no cambia.
- Los `.env` se materializan desde OpenBao: editarlos en el VPS se revierte en
  la siguiente pasada del timer.
