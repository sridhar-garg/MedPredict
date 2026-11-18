# Reference-inspired workspace update

Branch: `design/reference-inspired-ui`. Entry point: `app.py`.

## Page designs

Each feature has a full page header, its own colour family, and a motif suited to
the tool. Page backgrounds, active navigation, focus states, controls and related
dashboard cards follow that palette in light and dark appearances.

| Workspace | Colour and presentation |
| --- | --- |
| Heart health | Coral, pulse motif and circular illustration |
| Diabetes | Deep blue, measurement grid and square corners |
| Breast cancer | Berry rose, ribbon and asymmetric corners |
| Screenings | Amber worksheet, numbered header and ruled forms |
| Imaging and reports | Slate blue, scan frame and blueprint grid |
| AI assistant | Violet conversation header and chat bubbles |
| Accessibility | Teal, Braille illustration and larger control labels |
| Disease atlas | Olive and ivory, book typography and source cards |
| History | Copper, ruler motif and timeline borders |
| Family | Forest green and connected circle motifs |
| Account | Cyan frame and matching profile accent |
| Reviews | Gold, quotation motif and editorial typography |

Every dashboard tool container now has an explicit keyed colour rule and a 6px
top border. The previous mixture of selective card rules was removed. Assessment
workflow headings and all four steps are a single compact section; the steps
use four columns, two at intermediate widths and one on phones. Larger body
text, 48px controls, scrolling tabs, stacked forms and the mobile menu remain.

## Conditions and conversations

The bundled NLM library contains 151 selected common conditions and 1,017 health
topics. Search works locally, including epilepsy and spelling suggestions.
Users can browse by body system, read condition guides and follow source links.
Related assessment or screening buttons appear only where an existing tool is
relevant. These guides do not represent new trained prediction models. See
[condition library provenance and rebuild instructions](CONDITION_LIBRARY.md).

The assistant offers online Gemini and an explicitly labelled condition guide.
It can answer a greeting and retrieve condition information without API access.
Online calls use a current SDK, a bounded timeout, a larger response budget and
low thinking mode for Gemini 3. A model-not-found response triggers discovery of
models actually available to the configured key and at most one replacement
request. Quota and permission failures do not trigger repeated requests.
If online chat fails, users receive a guide answer with a clear source label and
an online retry option. Saved conversations preserve their answer-source metadata.
No provider error text or credentials are displayed or logged by this handler.

Reviews now contain only Community reviews and Write a review. Fictional sample
content and the Real-life usage tab have been removed. The navigation and
dashboard say Breast cancer, including the translated labels.

## Google sign-in

Continue with Google remains implemented using Streamlit native OIDC. Its button
is enabled when real Google credentials are configured in Streamlit Secrets;
password sign-in remains available. See [Google login setup](GOOGLE_LOGIN_SETUP.md).
Existing account linking and Google subject mapping are unchanged.

## Verification and deployment

- Forty pytest checks cover existing persistence and Google login, local search,
  condition routes, source provenance, provider failures and model discovery,
  saved conversations, retries, real review submissions and assessment rendering.
- Python compilation and Git whitespace checks pass.
- Thirty-three declared palette/header foreground and background pairs were
  calculated at 4.63:1 or higher. This is not a complete accessibility audit.
- Browser visual QA remains blocked by the environment's URL policy. Phone
  breakpoint rules were reviewed; no new screenshots or physical-device checks
  are claimed. Existing preview images show an earlier revision.
- Live Gemini and Google OAuth callbacks were not tested: production credentials
  are not available locally. The deterministic guide and simulated provider
  success/failure paths were tested. Camera recognition was not exercised.
- The public Streamlit source link points to this branch, but an authenticated
  production session and a manual cloud reboot are unavailable here. Publication
  to GitHub is separate from verification that Streamlit has reloaded the commit.
  If the old view persists, open the app's owner dashboard, verify this branch and
  `app.py`, and reboot the app. Hosted database setup remains separate.
