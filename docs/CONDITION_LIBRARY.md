# Condition library provenance

The committed `data/condition_library.json.gz` contains 1,017 English MedlinePlus
health topics, including 151 selected common conditions. `common_conditions.txt`
identifies the curated condition selection. It is a broad educational collection,
not a prevalence ranking and not a set of disease prediction models.

Source: **MedlinePlus.gov, U.S. National Library of Medicine**. MedPredict is not
endorsed by NLM. Topic summaries retain the source wording; images and logos are
not included. Topic pages and source articles remain linked from each guide.

- [Official XML data documentation](https://medlineplus.gov/xml.html)
- [MedlinePlus content use guidance](https://medlineplus.gov/about/using/usingcontent/)
- Source archive: `https://medlineplus.gov/xml/mplus_topics_compressed_2026-11-18.zip`
- Extracted XML SHA-256: `6943e975d74d503d1f1e5ad64ecbad783848d162758b5cfad99fcc516e3ef605`
- Snapshot: 18 November 2026. Content does not silently update while the app runs.

## Rebuild

Download the latest archive linked by the official XML page, extract the XML, then
run from the repository root, passing the actual archive URL for provenance:

```sh
python scripts/build_condition_library.py --xml /path/to/topics.xml --source-url https://medlineplus.gov/xml/mplus_topics_compressed_2026-11-18.zip
python -m pytest -q tests/test_condition_library.py tests/test_health_assistant.py
```

The builder extracts English titles, aliases, body groups, plain-text summaries
and selected source links, then writes deterministic gzip output. Review changed
condition titles and source content before committing an updated snapshot.

## Search and scope

Search ranks exact names and aliases first, then partial names, question tokens
and close spellings. The initial browser shows the common-condition selection;
the searchable picker exposes the full list, and submitted searches cover all
health topics. The app requires no MedlinePlus web-service call to open a guide.

The overview contains the source summary. Symptoms/tests and care/prevention
panels link to relevant source articles rather than inventing clinical details.
Related tools are explicit links to existing assessments or screening formulas;
other topics remain educational guides. The assistant's Condition guide mode
retrieves these summaries and labels them separately from online AI responses.
