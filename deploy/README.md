# Independent app deployment

This branch is the reference-inspired MedPredict UI with a direct, containerized
Python server. It does not use the Streamlit Community Cloud hosting page.
The existing website and design branch stay untouched.

Deploy the repository's `deploy/medpredict-app` branch as a Dockerfile service.
The public HTTPS domain is served on the provider's `PORT` (default 7860).
Set the deployment health check to `/_stcore/health` and allow sufficient time
for the first container startup. The service requires a suitably sized Python
host; CPU model weights are installed without CUDA packages.

Set the following values privately in the hosting service's Variables/Secrets
interface. Never put actual values in GitHub, the APK, the EXE, or chat.

* `APP_BASE_URL`: the new public HTTPS origin (or use `RAILWAY_PUBLIC_DOMAIN`).
* `DATABASE_URL`: the **same** existing server-only PostgreSQL connection URI,
  or a separately migrated, verified durable database. The startup will not
  initialize a new shared account database without permission.
* `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: existing Google web OAuth client.
* `MEDPREDICT_COOKIE_SECRET`: a stable, random secret of at least 32 characters.
* `GEMINI_API_KEY` and optionally `GEMINI_MODEL`: existing assistant settings.
* `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`: existing email/OTP/family settings.

In Google Cloud's OAuth client configuration, add the new `APP_BASE_URL` as an
authorized JavaScript origin and `APP_BASE_URL/oauth2callback` as an authorized
redirect URI. Retain the old Streamlit values while the new app is tested.
The cookie secret belongs only on the server; cookies are scoped to the new
domain, so existing users sign in on that domain once.

Verify the public login screen, a synthetic test login and saved results,
all important pages, Google OAuth, email, and Gemini before distribution.
The `/.well-known/assetlinks.json` endpoint contains only the public Android
signing-certificate fingerprint, to let the browser independently verify the
Android app's association with the owned deployment origin. Reuse the original
signing key for updates. No private signing material belongs in this repo.

The Android and Windows build scripts require the verified `--app-url` of
the new deployment. Do not distribute test binaries built for a placeholder.
