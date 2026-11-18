# Activate Google sign-in

The Google sign-in flow is implemented on `design/reference-inspired-ui`. It uses
Streamlit's native OIDC support, with Google as the identity provider. Real client
credentials must be configured before the button is enabled. Username/password
and the existing email-OTP account flow remain available.

## Google Cloud

1. Open the Google Auth Platform in your Google Cloud project. Complete Branding
   and Audience for MedPredict, using your own contact details. If the app is in
   Testing, add the Google accounts that will try the exhibit as test users.
2. Under Clients, create an OAuth client with type **Web application**.
3. Add this exact authorized redirect URI:

   ```text
   https://medpredictgit-gwv3verd6e57qygyixu5zs.streamlit.app/oauth2callback
   ```

   For a local installation on port 8501, also register:

   ```text
   http://localhost:8501/oauth2callback
   ```

4. Keep the client ID and client secret private. The app requests only
   `openid profile email`, using Streamlit's default account chooser.

## Streamlit

1. Open your app's **Manage app → Settings → Secrets**.
2. Copy the structure in [secrets.example.toml](../.streamlit/secrets.example.toml).
   Replace all `REPLACE_...` values with your Google client credentials and a
   strong randomly generated cookie secret. Keep any existing unrelated secrets.
   For local work, use the ignored `.streamlit/secrets.toml` instead.
3. The `redirect_uri` must exactly match the registered Google URI for that host.
   Keep `server_metadata_url` set to Google's documented discovery endpoint.
4. Save and reboot the app so `streamlit[auth]==1.67.0` is installed and the new
   configuration is loaded. The **Continue with Google** button becomes active.
5. Sign in with a test Google account, save a result, log out and sign in again.
   Confirm the account's saved work is restored.

Never put a real client secret or cookie secret in GitHub, chat, screenshots or
client-side HTML. ID and access tokens are not exposed by this configuration.

## Accounts and saved work

- A Google subject ID, rather than an email address, identifies returning users.
- A new Google user receives a normal MedPredict account and private workspace.
- If an existing account uses the same email, the user first signs in with that
  account's username/password. Only then is Google connected to the account.
  The app does not silently merge accounts or grant access based on email alone.
- Later Google sign-ins restore the same user ID, histories and permissions.
- Logging out clears both private session state and Streamlit's identity cookie.
- Provider issuer, audience, verified email and token lifetime are checked before
  creating a session. Streamlit/Authlib handles the signed OIDC exchange, nonce
  and state validation.

SQLite creates the identity table automatically. For an existing hosted Postgres
schema, apply [002_google_identities.sql](../db/002_google_identities.sql) before
enabling Google. Fresh installations use the updated [schema.sql](../db/schema.sql).
Hosted database activation remains separate from configuring Google sign-in.

Google sign-in must run in a supported browser. The existing Android WebView host
needs a separate system-browser authentication integration before it can support
Google OAuth; this update does not rebuild the APK.

## References and verification limits

- [Streamlit login configuration](https://docs.streamlit.io/develop/api-reference/user/st.login)
- [Streamlit identity claims](https://docs.streamlit.io/develop/api-reference/user/st.user)
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)

The code is tested with synthetic identities, database isolation checks and
mocked native-login calls. A real Google callback and production credentials have
not been exercised. The repository contains only a configuration example.
