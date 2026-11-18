"""Offline MedlinePlus search and routes to the app's actual assessment tools."""
from difflib import SequenceMatcher
from functools import lru_cache
import gzip
import json
from pathlib import Path
import re
import unicodedata


@lru_cache(maxsize=1)
def library():
    with gzip.open(Path(__file__).parent / "data/condition_library.json.gz", "rt", encoding="utf-8") as source:
        return json.load(source)


def normalize(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def search_topics(query="", *, common_only=False, group=None, limit=40):
    query = normalize(query)
    words = set(query.split()) - {"what", "is", "are", "a", "an", "the", "about", "explain", "tell", "me", "of", "for", "symptoms", "treatment", "prevent", "prevention", "in", "simple", "terms", "can", "you", "help", "with", "to", "how", "does", "do", "my", "and", "please", "condition", "risk", "manage"}
    scored = []
    for topic in library()["topics"]:
        if common_only and not topic["featured"]:
            continue
        if group and group not in topic["groups"]:
            continue
        names = [normalize(topic["title"])] + [normalize(a) for a in topic["aliases"]]
        if not query:
            score = 1
        elif query in names:
            score = 1000
        elif any(query in name for name in names):
            score = 700
        elif words and any(words <= set(name.split()) for name in names):
            score = 600
        else:
            similarity = max(SequenceMatcher(None, query, name).ratio() for name in names)
            score = 300 * similarity if similarity >= .76 else 0
        if score:
            scored.append((score, topic))
    scored.sort(key=lambda pair: (-pair[0], not pair[1]["featured"], pair[1]["title"]))
    return [topic for _, topic in scored[:limit]]


def related_tool(topic):
    slug = topic["url"].rsplit("/", 1)[-1]
    if slug in ("diabetes.html", "diabetestype2.html", "prediabetes.html"):
        return dict(page="pages/diabetes_app.py", label="Open diabetes risk assessment")
    if slug in ("heartdiseases.html", "coronaryarterydisease.html"):
        return dict(page="pages/heart_app.py", label="Open heart risk assessment")
    if slug == "breastcancer.html":
        return dict(page="pages/breast_app.py", label="Open breast cancer assessment")
    screening = {
        "highbloodpressure.html": "High blood pressure", "chronickidneydisease.html": "Chronic kidney disease indicators",
        "anemia.html": "Anaemia indicators", "cholesterol.html": "High LDL cholesterol",
        "obesity.html": "Obesity / BMI", "sleepapnea.html": "Sleep apnoea screening",
        "fattyliverdisease.html": "Liver fibrosis screening", "steatoticliverdisease.html": "Liver fibrosis screening",
    }.get(slug)
    if screening:
        return dict(page="pages/4_health_screenings.py", label="Open related screening", screening=screening)
    return None


def counts():
    topics = library()["topics"]
    return len(topics), sum(topic["featured"] for topic in topics)
