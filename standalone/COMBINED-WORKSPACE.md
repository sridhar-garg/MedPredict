# Aroham AI — four applications, one account

This separate branch contains the authorized combined editions of MedPredict,
Healthara, Namastey AI and Kaamigo. Original deployments and databases are left
untouched. Android package/app name is Aroham AI (app.aiworkspace.mobile);
Windows is Aroham-AI.exe with its own local port, 8766.

Version 1.1 adds shared appearance and language preferences. The host owns
both settings, saves them to the Google-owned profile, caches changes locally
when offline, and supplies them to every integrated module. Theme controls
inside Healthara and Kaamigo update the shared setting, not a separate local
theme. English and 14 additional UI languages are bundled, using the
existing MedPredict catalogs and expanded workspace catalogs. Hindi has the
largest new coverage. Untranslated original educational content, user text
and report/model values stay unchanged.

Version 1.1.1 uses a compact outer toolbar and removes duplicate embedded
banners. The Windows launcher and existing callback/port are unchanged.
Keep the little launcher window open or minimized while using the workspace.
Dashboard localization covers the main activity/card strings in all 15
languages, with expanded German/Hindi module UI strings. Original long
educational content and user-authored text are still not automatically
translated. Healthara no longer presents sample hydration, sleep, steps
or completed indicators as personal data; the shared snapshot updates both
dashboards, with manually entered sleep/steps and saved water counts.

Version 1.1.2 expands the same UI catalog to all 14 non-English languages
across the combined dashboard and the four individual apps. The build
rejects any missing catalog entries in any locale; the localization test
also checks each dashboard state, representative module controls, language
switching, and dynamic counts. Multiline labels are supported. Long original
articles, source material and free-form user data remain in their original
language. The footer shows the installed version so older builds are easy
to recognize.

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

Supabase project (existing name): AI Workspace, Mumbai, ref lfysbdtkysbomfgubofi.
The schema in backend/schema.sql and backend/workspace.sql has been applied.
The language column migration in backend/preferences.sql has also been applied.
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
