# MedPredict standalone applications

This separately maintained app is not a wrapper around a hosted Streamlit site.
All three trained five-model assessment ensembles, the condition atlas, seven
educational screening calculations, responsive UI, report-text extraction and
English Grade-1 Braille translation ship as local assets.

Android: installs under the existing application ID, loads assets from a
restricted local HTTPS WebView origin, and opens the system browser for Google.
Windows: a portable 64-bit GUI executable containing the complete resource
bundle. It serves only fixed resources on 127.0.0.1:8765 on the current device;
Chrome or Edge provides the app window. No external presentation or Python
process is required. Exit from the MedPredict control window to stop the
local service. The Windows binary is not Authenticode-signed.

## Optional cloud services

An offline preview builds with no project URL or key. Sessions are in memory
and offline demonstration history is cleared at sign-out. Google login,
cross-device history, family sharing, reviews and online Gemini require the
approved cloud project and configuration. Only Google is an interactive
authentication provider; no independent username/password account is offered.

1. Create a free Supabase project under the owner's selected organisation.
2. Apply `backend/schema.sql` after confirming the project has no conflicting
   schema. Check RLS, policies and grants before storing any data.
3. Set up the Google OAuth provider with a Google web OAuth client. Register
   `https://PROJECT_REF.supabase.co/auth/v1/callback` in Google Cloud. Configure
   exact application redirect URLs `http://127.0.0.1:8765/auth/callback` and
   `app.medpredict.mobile://auth-callback` in Supabase. Disable other providers
   and email/password signup. Do not copy existing OAuth client secrets into the
   client bundle.
4. Deploy `backend/assistant/index.ts` as `medpredict-assistant`. It validates
   the user's bearer session and Google provider before calling a fixed Gemini
   model. Set `GEMINI_API_KEY` and `GEMINI_MODEL` as function secrets. Keep all
   private service keys and OAuth credentials on the server.
5. Build both apps with `--url` and the project's **publishable** key (`--key`).
   Do a real Google sign-in and synthetic-record create/read/delete test in
   both apps before distributing the connected release.

## Build and validation

Use the existing Python scientific-model environment to run
`python standalone/export_assets.py --output /path/to/assets --fixtures /path/to/fixtures.json`.
The native builder uses the official Android SDK (aapt2, D8, zipalign,
apksigner), the existing private signing key for upgrades, Zig's Windows
cross-compiler, Pillow, and PDF.js. Run `python standalone/build_native.py --help`
for paths. With `--stage-only`, it creates an unpacked web bundle for local tests.
The build script rejects service-role keys.

`qa.mjs` compares model estimates with 99 synthetic input fixtures exported
from the original Python pipelines, and contains a Chromium smoke test for
the desktop and phone UI. The legacy experimental Torch imaging and webcam
ASL/ISL classifiers are not yet ported; the local image viewer explicitly
does not classify images. PDF extraction works with text-based documents,
not scanned-image OCR. All outputs are educational, not diagnostic.
