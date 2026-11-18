# Reference-inspired UI: exhibition and mobile update

Changes are on `design/reference-inspired-ui`. The violet/navy reference design,
studio photograph, existing Android host and assessment models are retained.

## Phone experience

- A compact Menu opens all dashboard, assessment, accessibility, review and account pages.
- Settings exposes the interface language and appearance on every workspace page.
- Below 769px, forms and cards stack, navigation no longer overlays the page,
  controls have larger touch areas, and inputs use 16px text.
- Long labels wrap. Tabs and data tables keep their own horizontal scrolling.
- The Braille teaching cell keeps its correct two-column dot layout.
- Chat spacing and bottom padding accommodate narrow screens and device safe areas.

## Exhibition features

A medical-kit logo replaces the pulse mark. Assessments, imaging, assistant,
accessibility and reviews use distinct colour accents with stronger text contrast.
Accessibility is a full dashboard card within MedPredict.

English is the default; fourteen additional offline interface catalogs provide
Indian and international choices, including Arabic direction support. Common
navigation, headings, form labels and review controls are translated. Specialist
medical text, research explanations and uncovered copy remain in English. Model
option values, user submissions and conversations are not translated. The language
and appearance preferences are attached to the signed-in account.

Visitors can submit, edit or delete one consented public review per account.
Community ratings are calculated from these submissions. The original three
fictional examples are labelled and kept in a separate sample tab.

History now includes saved screenings, report measurements, imaging outputs,
completed chats, and explicitly saved accessibility text. It provides per-item
export and deletion. Camera frames and original scans are not stored. See
[database setup](DATABASE_SETUP.md) before activating hosted Postgres.

## Validation

- Eight pytest checks cover language switching, review submission and updates,
  screening saves, fresh-process review persistence, private account isolation,
  family sharing permissions, preferences and database constraints.
- Streamlit AppTest rendered all three assessment forms, medical imaging and
  profile without exceptions or app errors.
- Browser checks at 320px, 390px and 768px found document width equal to viewport
  width. Phone login/signup, assessment controls, menu, settings and review tabs
  were exercised. Arabic right-to-left presentation was checked at 768px.
- Light and dark phone appearances were reviewed, alongside the desktop dashboard. Desktop Menu interaction and expanded sidebar navigation were also checked.
- Python compilation and Git whitespace checks pass.

## Limits and deployment

Browser QA uses an ignored synthetic-session fixture and a 320/390/768px iframe;
this is not physical-device validation. Test accounts and the fixture are excluded
from Git. Actual camera permission/recognition, email delivery, external AI
responses and cloud database connectivity were not exercised.

Existing models emit a scikit-learn version mismatch warning in the local runtime;
presentation checks do not establish clinical performance or model reproducibility.

The connected Supabase account has no project. The schema, migration helper and
server integration are prepared, but hosted persistence requires project creation
and a private `DATABASE_URL` in Streamlit Secrets. SQLite is used until then and
is not durable across temporary-host redeploys. No cloud connection is claimed.

Push this branch to update its source. Production rollout follows the existing
Streamlit branch configuration; hosted deployment status has not been verified.
