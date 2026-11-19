# Deploy MedPredict to an owner-controlled Linux VM

This is a direct HTTPS deployment for Android and Windows, intended for an
Oracle Cloud **Always Free** Ampere A1 VM with sufficient available memory.
It is not a trial-only hosting configuration. Free-plan eligibility, instance
capacity, idle-instance reclamation and service policies remain the provider's
responsibility. Do not provision paid resources or upgrade without approval.

## Prerequisites

* An owner-created Oracle Cloud account on the Free Tier, and an Always Free
  Arm Linux VM (Ubuntu 24.04 LTS aarch64 recommended). Select a home-region
  shape within the current console's Always Free entitlement; do not select a
  paid shape. Keep a copy of the private SSH key outside the repo.
* Public IPv4 address and an owned or controlled public DNS hostname pointing
  to it. The hostname is necessary for valid HTTPS, Google OAuth and Android
  Digital Asset Links. Do not install the apps against a bare HTTP address.
* Install Docker Engine and the Compose v2 plugin from the supported Ubuntu
  packages or Docker's official instructions.
* Cloud firewall: allow HTTPS TCP 443 and HTTP TCP 80 for certificate issuance
  and redirect, optionally UDP 443 for HTTP/3, SSH only from the administrator's
  approved source. Do not expose port 7860, 8501 or any database port.

## Configuration

Clone the public GitHub repo on the VM, using the `deploy/medpredict-oci` branch.
All secrets are entered directly on the VM, never committed or pasted in chat.

```sh
sudo install -d -m 700 /etc/medpredict
sudo nano /etc/medpredict/host.env
sudo nano /etc/medpredict/app.env
sudo chmod 600 /etc/medpredict/host.env /etc/medpredict/app.env
```

`host.env` contains only the actual public hostname (no scheme or path):

```dotenv
MEDPREDICT_PUBLIC_HOST=your-actual-hostname.example
```

`app.env` contains the existing private OAuth, Gemini and email configuration:

```dotenv
GOOGLE_CLIENT_ID=YOUR_EXISTING_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_EXISTING_CLIENT_SECRET
MEDPREDICT_COOKIE_SECRET=YOUR_STABLE_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
GEMINI_API_KEY=YOUR_EXISTING_KEY
GEMINI_MODEL=YOUR_CURRENT_MODEL
GMAIL_ADDRESS=YOUR_EXISTING_ADDRESS
GMAIL_APP_PASSWORD=YOUR_EXISTING_APP_PASSWORD
```

Confirm the account database choice before starting:

* **Preserve shared records:** set `MEDPREDICT_STORAGE=postgres` and
  `DATABASE_URL` to the existing PostgreSQL URI. Existing users remain in that
  storage. Do not repurpose a database credential without the owner's approval.
* **Fresh independent persistent records (only if approved):** set
  `MEDPREDICT_STORAGE=sqlite` and `MEDPREDICT_DB_PATH=/data/healthai.db`. Do not
  set `DATABASE_URL`. The app refuses to start unless `/data` really is mounted.
  Both installed apps use the same server data, but old Streamlit-only records
  are not automatically copied. An owner-approved SQLite backup can be restored
  before first startup; verify schema and record counts separately.

In the existing Google OAuth client, append `https://<hostname>` as an
authorized origin and `https://<hostname>/oauth2callback` as a redirect URI.
Keep the existing Streamlit entries. Caddy will obtain a public TLS certificate
when DNS and the cloud firewall are configured correctly.

From the repository root:

```sh
sudo docker compose --env-file /etc/medpredict/host.env -f deploy/oci/compose.yaml up -d --build
sudo docker compose --env-file /etc/medpredict/host.env -f deploy/oci/compose.yaml ps
```

The heavy CPU-only AI dependencies may take time to build. If a dependency or
health check fails, diagnose that build; do not disable authentication or TLS.
The app container is reachable only on its internal Compose network. Only the
HTTPS proxy accepts public traffic; it forwards the app's WebSockets.

## Verify before distributing

Check the HTTPS login page, `/_stcore/health`, and
`/.well-known/assetlinks.json`, including its signing-certificate fingerprint.
Test synthetic accounts, Google login, email, Gemini and feature pages. The
APK/EXE must be rebuilt with the confirmed HTTPS hostname, preserving the
Android signing key. Do not distribute a binary with a placeholder URL.

Back up the data and retain an encrypted copy outside the VM. When using
SQLite, use its online backup API rather than copying a live WAL-mode file.
Never run Compose with `down -v` unless the owner explicitly intends to delete
the persistent data and certificates. The original Streamlit site is unchanged.
