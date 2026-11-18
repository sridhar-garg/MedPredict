# Durable account storage

MedPredict is a Python Streamlit server. It uses its existing verified-email and
hashed-password login, not Supabase Auth. Database calls execute on that trusted
server; no database credential or password hash is sent to the browser.

## Supabase setup

Google sign-in has a separate [setup guide](GOOGLE_LOGIN_SETUP.md). Existing
hosted schemas must also apply `db/002_google_identities.sql` before enabling it.

1. Create/select the MedPredict Supabase project, preferably Mumbai (`ap-south-1`).
2. Apply `db/schema.sql` using the SQL editor or the Supabase connector. Its
   `medpredict` schema is private and must **not** be added to exposed API schemas.
3. Use the Supabase **Connect** dialog to copy the session-pooler Postgres URI
   (port 5432 supports Streamlit hosts with IPv4). Set its actual password privately
   in Streamlit app settings → Secrets:

   ```toml
   DATABASE_URL = "postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres"
   ```

   Keep the URI out of git, chat, client HTML and screenshots. Environment
   `DATABASE_URL` works as well. Connections require TLS. The admin URI works with
   owner access; use a dedicated server login for a production deployment. Grant
   that server role usage on `medpredict`, CRUD on its tables, sequence usage,
   and explicit server-role RLS policies. Never grant these to API roles.
4. Restart the app, submit an assessment/review, log out, log in again and check
   History and Reviews. A configured cloud connection failure raises an error;
   the app never silently switches back to SQLite.

Without `DATABASE_URL`, a local SQLite database is used. For a hosted app whose
filesystem is temporary, this is not durable across redeploys. Local installations
can set `MEDPREDICT_DB_PATH` to a persistent disk path. No hosted project was
available in the connected account at implementation time; cloud activation
requires selection of the organization and project creation.

## Existing accounts and data

An existing SQLite deployment is **not** automatically imported. Before switching,
back up the running app's `healthai.db`. Use `python db/import_sqlite.py PATH`
with `DATABASE_URL` set privately to copy all six tables transactionally into an
empty hosted schema. IDs, password hashes, family invitations and histories are
preserved. The importer refuses a nonempty target; it never merges or overwrites
accounts. Keep the original backup until login and history have been verified.

## Saved data

- Main assessments: inputs, estimates and evaluations in Health History.
- Seven extra screenings: measurements, source reference and result summary.
- Imaging: model identifier and research scores; original images are not stored.
- Reports: verified extracted measurements, age and equation coefficient.
- AI assistant: completed conversation snapshots; latest restores on return.
- Accessibility: explicit Save controls for Braille and recognized sign text;
  no camera recordings are saved.
- Family connections, profile, language and appearance preferences.
- Reviews: one public, consented review per account, editable and removable.

Private workspace items can be exported/deleted in History. Review statistics
exclude the three fictional original examples. Submitted reviews identify an
account submission; they are not independently verified testimonials or clinical
validation.

## Languages

English is the default. Fourteen offline catalogs cover navigation, common form
labels, dashboard and feedback UI. They never send user text to a translation
service or change internal model input values. Specialist clinical explanations,
research content, user submissions and third-party model labels may remain in
English. Arabic uses right-to-left presentation with English numeric inputs kept
left-to-right. Native-speaker review is recommended before expanding translated
clinical terminology.
