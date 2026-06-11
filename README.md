# S3 Portal

A minimal FastAPI service that lets authenticated users browse and download files from an
S3-compatible bucket via a simple web UI, and lets in-cluster services push files via a
REST API secured with an API key.

## Architecture

```
Browser user  ──OIDC login──►  FastAPI  ──list / presign──►  S3 bucket
In-cluster pod ──X-API-Key──►  POST /upload/{key}         ──put_object──►  S3 bucket
```

## Prerequisites

- Python 3.11+
- [Podman Desktop](https://podman-desktop.io/) (or Docker)
- A Keycloak instance (see below)

---

## Local development setup

### 1 — Python environment

```powershell
cd D:\source\s3-portal
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### 2 — Start MinIO (local S3)

```powershell
podman run -d --name minio `
  -p 9000:9000 -p 9001:9001 `
  -e MINIO_ROOT_USER=minioadmin `
  -e MINIO_ROOT_PASSWORD=minioadmin `
  docker.io/minio/minio server /data --console-address ":9001"
```

Create the bucket:

```powershell
podman exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
podman exec minio mc mb local/s3-portal-dev
```

MinIO web console: **http://localhost:9001** (minioadmin / minioadmin)

### 3 — Start Keycloak (local OIDC provider)

```powershell
podman run -d --name keycloak `
  -p 8080:8080 `
  -e KEYCLOAK_ADMIN=admin `
  -e KEYCLOAK_ADMIN_PASSWORD=admin `
  quay.io/keycloak/keycloak start-dev
```

Then open **http://localhost:8080** → Administration Console → log in with `admin` / `admin`.

#### Create a Realm

- Top-left dropdown → **Create Realm**
- Name: `s3-portal` → **Create**

#### Create a Client

In the `s3-portal` realm → **Clients** → **Create client**

| Field | Value |
|---|---|
| Client type | OpenID Connect |
| Client ID | `s3-portal` |
| Client authentication | ON |
| Standard flow | ON |
| Valid redirect URIs | `http://localhost:8000/auth/callback` |
| Web origins | `http://localhost:8000` |

Save, then open the **Credentials** tab and copy the **Client secret**.

#### Create a test user

**Users** → **Create user**

| Field | Value |
|---|---|
| Username | `testuser` |
| Email | `test@example.com` |
| Email verified | ON |

Go to the **Credentials** tab → **Set password** → set a password → turn **Temporary** OFF.

### 4 — Configure `.env`

```powershell
cp .env.example .env
```

Edit `.env`:

```dotenv
S3_BUCKET=s3-portal-dev
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://localhost:9000

OIDC_ISSUER=http://localhost:8080/realms/s3-portal
OIDC_CLIENT_ID=s3-portal
OIDC_CLIENT_SECRET=<paste secret from Keycloak Credentials tab>
OIDC_REDIRECT_URI=http://localhost:8000/auth/callback

UPLOAD_API_KEY=local-dev-key
SECRET_KEY=any-random-string
```

### 5 — Run the app

```powershell
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — you will be redirected to Keycloak. Log in as `testuser`
and you will land on the file browser.

---

## Testing the upload API

Files are pushed with a `POST /upload/{key}` request authenticated by the `X-API-Key`
header. The `key` can include path segments to organise files in the bucket.

### Upload a text file

```powershell
curl -X POST http://localhost:8000/upload/test/hello.txt `
     -H "X-API-Key: local-dev-key" `
     -H "Content-Type: text/plain" `
     --data-binary "hello from a pod"
```

### Upload a binary file

```powershell
curl -X POST http://localhost:8000/upload/images/photo.png `
     -H "X-API-Key: local-dev-key" `
     --data-binary "@C:\path\to\photo.png"
```

Content-Type is inferred from the file extension when the header is omitted.

### Upload to a nested path

```powershell
curl -X POST http://localhost:8000/upload/my-service/2024/06/report.csv `
     -H "X-API-Key: local-dev-key" `
     -H "Content-Type: text/csv" `
     --data-binary "@C:\path\to\report.csv"
```

A successful upload returns HTTP 201:

```json
{"key": "test/hello.txt", "bucket": "s3-portal-dev", "size": 16}
```

Refresh the browser to see the uploaded file appear in the list.

---

## Running the test suite

```powershell
pytest tests/ -v
```

---

## Production notes

- Replace `UPLOAD_API_KEY=local-dev-key` with a strong random value:
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Store the key in a Kubernetes Secret and mount it as an environment variable in both
  the portal pod and any uploader pods.
- Apply `k8s/networkpolicy.yaml` to restrict which pods can reach the upload endpoint
  at the network layer.
- Label uploader pods with `app.kubernetes.io/component: uploader` to match the policy.
