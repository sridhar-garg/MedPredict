from urllib.parse import urlparse

from condition_library import counts, library, related_tool, search_topics


def test_bundled_library_has_substantial_sourced_condition_coverage():
    total, common = counts()
    assert common >= 100 and total >= 1000
    topics = library()["topics"]
    assert len({topic["id"] for topic in topics}) == total
    for topic in topics:
        source = urlparse(topic["url"])
        assert source.scheme == "https" and source.hostname == "medlineplus.gov"
        assert topic["title"] and topic["summary"] and topic["groups"]
        assert "<img" not in topic["summary"]


def test_exact_alias_typo_and_question_search_need_no_network():
    for query in ("epilepsy", "epilepcy", "What is epilepsy?", "Explain epilepsy in simple terms"):
        topic = search_topics(query)[0]
        assert topic["title"] == "Epilepsy"
        assert "seizure" in topic["summary"].lower()
    assert search_topics("high blood pressure")[0]["title"] == "High Blood Pressure"
    assert search_topics("zzzzzzzzzzzz") == []
    assert len(search_topics(common_only=True, limit=2000)) == counts()[1]


def test_filters_and_routes_only_offer_existing_related_tools():
    asthma = search_topics("asthma")[0]
    group = asthma["groups"][0]
    assert all(group in item["groups"] for item in search_topics(group=group, limit=2000))
    assert related_tool(search_topics("epilepsy")[0]) is None
    assert related_tool(search_topics("breast cancer")[0])["page"] == "pages/breast_app.py"
    assert related_tool(search_topics("high blood pressure")[0])["screening"] == "High blood pressure"
