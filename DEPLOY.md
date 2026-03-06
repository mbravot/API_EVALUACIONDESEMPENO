# Despliegue en Google Cloud Run (desde GitHub)

## Requisitos

- Proyecto en Google Cloud con **Cloud Run** y **Artifact Registry** (o Container Registry) habilitados.
- Repositorio en GitHub (ej. `mbravot/API_EVALUACIONDESEMPENO`).
- Si usas **Cloud SQL**: instancia configurada y, en Cloud Run, conexión (conexión privada o Cloud SQL Auth Proxy).

---

## Opción 1: Despliegue continuo desde GitHub (recomendado)

1. En [Google Cloud Console](https://console.cloud.google.com/) → **Cloud Run** → **Crear servicio**.
2. Elige **Continuously deploy from a repository** (o **Second generation** y luego **Continuously deploy from a repository**).
3. Conecta tu cuenta de GitHub y selecciona el repo y la rama (ej. `main`).
4. **Build**: tipo **Dockerfile** y ruta `Dockerfile` (raíz del repo).
5. **Servicio**: nombre (ej. `api-evaluacion`), región, y configura **Variables de entorno** y/o **Secretos**:
   - `DATABASE_URL` o `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (según tu `config.py`).
   - `JWT_SECRET_KEY` (recomendado como secreto).
   - Si usas Cloud SQL: la conexión se suele configurar en el servicio (conector Cloud SQL).
6. Guarda. Cada **push a la rama** hará build y despliegue automático.

---

## Opción 2: GitHub Actions

1. En el repo de GitHub → **Settings** → **Secrets and variables** → **Actions**.
2. Añade secretos:
   - `GCP_PROJECT_ID`: ID del proyecto de Google Cloud.
   - `GCP_SA_KEY`: contenido JSON de una cuenta de servicio con permisos para Cloud Run y Artifact Registry (o usa Workload Identity).
3. Crea el workflow en `.github/workflows/deploy-cloudrun.yml` (ver ejemplo más abajo).
4. Cada push a `main` (o el trigger que definas) desplegará en Cloud Run.

Ejemplo mínimo de workflow (ajusta nombre del servicio y región):

```yaml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud run deploy api-evaluacion \
            --source . \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated
```

---

## Variables de entorno en Cloud Run

Configúralas en el servicio (Cloud Run → tu servicio → **Variables and secrets**):

| Variable        | Descripción                          |
|----------------|--------------------------------------|
| `DATABASE_URL` | URL de conexión MySQL (si usas una sola variable) |
| `DB_HOST`      | Host de la base de datos             |
| `DB_USER`      | Usuario MySQL                        |
| `DB_PASSWORD`  | Contraseña (usa **Secret Manager**)  |
| `DB_NAME`      | Nombre de la base                    |
| `JWT_SECRET_KEY` | Clave JWT (usa **Secret Manager**) |

`PORT` la define Cloud Run (no hace falta configurarla).

---

## Build local (probar la imagen)

```bash
docker build -t api-evaluacion .
docker run -p 8080:8080 -e DATABASE_URL="mysql+pymysql://user:pass@host/db" api-evaluacion
```

Luego: `http://localhost:8080/api/test-db`
