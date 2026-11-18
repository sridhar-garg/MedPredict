# Colour, readability and Google sign-in update

Branch: `design/reference-inspired-ui`.

The main workspace now uses teal, navy and neutral surfaces. Each tool keeps a
matching colour family between its dashboard card, contextual header and page
controls. Purple is used for the AI assistant.

| Tool | Colour family |
| --- | --- |
| Heart health | Coral |
| Diabetes and imaging | Blue |
| Breast health | Rose |
| Screenings and community reviews | Amber |
| Accessibility and account | Teal |
| Disease atlas and family health | Green |
| Saved history | Copper |
| AI assistant | Violet |

Cards have descriptive category labels, coloured borders, distinct icon surfaces
and matching actions. Each tool page adds a short contextual banner. Paragraphs
and form labels use 16px text; key descriptions use 17px, captions use 14px, and
card titles use 23px. Dark mode has a separate set of foreground/background pairs.
Phone stacking, 48px controls, scrolling tabs and Braille dot layout are retained.
The existing photograph is desaturated and placed behind a teal/navy treatment.
Assessment calculations and model files are unchanged.

## Google sign-in

The login page includes **Continue with Google**, using Streamlit's native OIDC
flow. Username/password and email-OTP account setup remain available. The button
is disabled with a clear availability message until real Google credentials are
configured in Streamlit Secrets. See [Google login setup](GOOGLE_LOGIN_SETUP.md).

Returning users are identified by their Google subject ID. Existing local accounts
must authenticate once with their username and password before Google is linked;
matching emails alone never grant access to an existing workspace. Logout clears
the Google identity cookie as well as private Streamlit session state. Claims are
checked for issuer, client audience, verified email and expiry.

## Validation

- All 24 pytest checks pass. These cover existing persistence and localization,
  invalid/expired identity rejection, stable identity mapping after an email
  change, account isolation, explicit linking, callback/session restoration,
  native login invocation, cookie logout and password-login fallback.
- Python compilation and Git whitespace checks pass.
- The measured palette text/background pairs have contrast ratios from 5.27:1
  upward, including light/dark tool labels and white text on primary actions.
  This is a calculation for the declared pairs, not a full accessibility audit.
- Browser visual QA was attempted but blocked by the environment's URL policy.
  No new browser screenshots or physical-device validation are claimed.
- Real Google OAuth callbacks, production credentials and live Streamlit
  deployment have not been verified. Client credentials are not available in this
  workspace. The committed configuration file contains placeholders only.

The previous screenshots in `docs/design-preview` document the preceding mobile
revision and do not show this new palette. Cloud persistence remains subject to
the separate database setup.
