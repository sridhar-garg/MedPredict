# AI Workspace — four applications, one account

This separate branch contains the authorized combined editions of MedPredict,
Healthara, Namastey AI and Kaamigo. Original deployments and databases are left
untouched. Android package/app name is AI Workspace (app.aiworkspace.mobile);
Windows is AI-Workspace.exe with its own local port, 8766.

## Identity and data

Only the workspace authenticates (Google OAuth via Supabase PKCE). Module
copies open in isolated sandboxed frames with a restricted message bridge.
They receive the signed-in display name, user ID and their own state, never
a Google or Supabase token, password, email or another application's records.
No old account is automatically linked by email.

Healthara's private saved wellness and journal state, Namastey AI's learning
progress and Kaamigo's listing activity contribute real dashboard summaries.
New Kaamigo marketplace listings are shared with signed-in users of the
combined edition only. The database applies Google-provider and owner RLS.
Existing independent histories, community listings and reviews are not migrated.

## Upstream sources

Authorized by the project team on 22 November 2026:
- https://github.com/sridhar-garg/MedPredict (bundled standalone core)
- https://github.com/frihita/Healthara_2.0 (adapted index.html)
- https://github.com/arhita536/Namastey-AI__ (adapted index.html)
- https://github.com/arhitajain/kaamigo (adapted index.html)

Independent login forms, EmailJS, Firebase integration and embedded remote
scripts have been removed from the adapted copies to prevent disclosure of
private workspace data. External chat, remote imagery/media, camera-based
recognition, GPS/map services and some PDF export functions are not available
in this build. MedPredict's portable fifteen models and seven screenings
are bundled; experimental imaging and recognition models remain unported.
Do not use prototype predictions for medical decisions.

## Free shared backend configuration

Project: AI Workspace, Mumbai, ref lfysbdtkysbomfgubofi.
The schema in backend/schema.sql and backend/workspace.sql has been applied.
The edge function medpredict-assistant is deployed, but requires Gemini
secrets configured by the owner.

1. Enable Google under Authentication > Providers using the existing Google
   web OAuth client. Add the project's callback to Authorized redirect URIs:
   https://lfysbdtkysbomfgubofi.supabase.co/auth/v1/callback
2. Set Site URL to http://127.0.0.1:8766 and add redirect URLs:
   - http://127.0.0.1:8766/auth/callback
   - app.aiworkspace.mobile://auth-callback
3. Disable other login providers and email/password signup. Do not place
   the OAuth client secret, Gemini key or service key in the client.
4. If needed, set GEMINI_API_KEY and a supported GEMINI_MODEL in Edge
   Function Secrets. MedPredict's offline guide does not require a key.
5. Build using standalone/build_native.py with this project's URL and
   publishable key. The Android app and Windows executable have separate
   identity from the MedPredict installers.

## Validation

Run `node standalone/hub.test.mjs` for synthetic shared identity, real
in-app routes, module state isolation, snapshot writes, marketplace and
dashboard aggregation. A database transaction tested owner isolation
and blocked non-Google identity, then rolled back its synthetic records.
All module inline scripts were parsed. The compiled APK signature and
metadata and Windows PE payload were verified. Live Google sign-in and
actual Android/Windows device UI still require testing after provider setup.
