"""Build an offline, source-attributed MedlinePlus topic library.

Usage: python scripts/build_condition_library.py --xml downloaded-topics.xml
Download the source from https://medlineplus.gov/xml.html. No images are included.
"""
import argparse
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class PlainSummary(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "h2", "h3", "ul", "ol"):
            self.parts.append("\n\n")
        if tag == "li":
            self.parts.append("\n• ")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("\n\n")


def summary_text(value):
    parser = PlainSummary()
    parser.feed(value or "")
    return "\n\n".join(" ".join(p.split()) for p in "".join(parser.parts).split("\n\n") if p.strip())


def build(source, source_url):
    raw = source.read_bytes()
    featured = set((ROOT / "data/common_conditions.txt").read_text().splitlines())
    records = []
    sections = {"Start Here": "Overview", "Symptoms": "Symptoms and tests",
                "Diagnosis and Tests": "Symptoms and tests", "Treatments and Therapies": "Care and prevention",
                "Prevention and Risk Factors": "Care and prevention", "Living With": "Care and prevention"}
    for node in ET.fromstring(raw).findall(".//health-topic"):
        if node.get("language", "").lower() != "english":
            continue
        url = node.get("url", "")
        if urlparse(url).hostname != "medlineplus.gov" or urlparse(url).scheme != "https":
            continue
        links, counts = [], {}
        for site in node.findall("site"):
            category = sections.get(site.findtext("information-category", ""))
            target = site.get("url", "")
            if category and urlparse(target).scheme == "https" and counts.get(category, 0) < 3:
                links.append(dict(section=category, title=site.get("title", "Read source"), url=target,
                                  organization=site.findtext("organization", "")))
                counts[category] = counts.get(category, 0) + 1
        records.append(dict(id=node.get("id"), title=node.get("title"), url=url,
                            summary=summary_text(node.findtext("full-summary", "")),
                            description=node.get("meta-desc", ""),
                            aliases=sorted({x.text for name in ("also-called", "see-reference")
                                            for x in node.findall(name) if x.text}),
                            groups=[x.text for x in node.findall("group") if x.text],
                            featured=node.get("title") in featured, links=links))
    records.sort(key=lambda item: item["title"].casefold())
    if sum(r["featured"] for r in records) < 100:
        raise ValueError("The common-condition selection must contain at least 100 source topics.")
    payload = dict(source="MedlinePlus.gov, U.S. National Library of Medicine", source_url=source_url,
                   source_sha256=hashlib.sha256(raw).hexdigest(), topics=records)
    target = ROOT / "data/condition_library.json.gz"
    target.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
    print(f"Bundled {len(records)} topics, including {sum(r['featured'] for r in records)} common conditions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()
    build(args.xml, args.source_url)
