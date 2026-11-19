# deploy/

Artefactos de despliegue en el VPS. El procedimiento completo, con OpenBao y
los secretos de GitHub, está en **[`docs/despliegue.md`](../docs/despliegue.md)**.

| Archivo | Destino en el VPS |
|---|---|
| `compose.yaml` | `/home/morfeo/residuos/compose.yaml` |
| `.env.example` | plantilla para cargar `secret/residuos/prod` en OpenBao |
| `residuos-deploy` | `/usr/local/bin/residuos-deploy` (lo instala el setup) |
| `13-deploy-residuos.conf` | `/etc/ssh/sshd_config.d/13-deploy-residuos.conf` |
| `setup-deploy-user.sh` | se ejecuta una vez como root desde este directorio |

Comprobación local del compose (sin tocar el VPS):

```powershell
$env:RESIDUOS_IMAGE_TAG = "sha-abc1234"
docker compose -f deploy/compose.yaml --env-file deploy/.env.example config
```
