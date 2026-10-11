"""MedlinePlus-backed disease search. No generative invented treatment guidance."""
from __future__ import annotations
from dataclasses import dataclass
from html.parser import HTMLParser
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

API="https://wsearch.nlm.nih.gov/ws/query"


class _PlainText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[]
    def handle_data(self,s):self.parts.append(s)
    def handle_starttag(self,tag,attrs):
        if tag in {'p','li','div','br','h1','h2','h3'}:self.parts.append('\n')

def clean_html(text: str, max_chars:int=4200) -> str:
    parser=_PlainText();parser.feed(text or '')
    joined=' '.join(' '.join(parser.parts).split())
    return joined[:max_chars]+('…' if len(joined)>max_chars else '')


def valid_source(url: str) -> bool:
    host=urlparse(url).hostname or ''
    return urlparse(url).scheme=='https' and (host=='medlineplus.gov' or host.endswith('.medlineplus.gov'))

@dataclass(frozen=True)
class Topic:
    title:str
    url:str
    summary:str


def parse_medlineplus(xml_text:str) -> list[Topic]:
    """XML MedlinePlus response; skip non-MedlinePlus or malformed URLs."""
    root=ET.fromstring(xml_text)
    out=[]
    for doc in root.findall('.//document'):
        url=doc.attrib.get('url','')
        if not valid_source(url):continue
        parts={el.attrib.get('name',''): ''.join(el.itertext()) for el in doc.findall('./content')}
        title=clean_html(parts.get('title',''),150)
        summary=clean_html(parts.get('full-summary') or parts.get('snippet') or parts.get('summary') or '',5000)
        if title:out.append(Topic(title,url,summary))
    return out


def lookup_topics(query:str, maximum:int=5) -> list[Topic]:
    import requests
    q=re.sub(r'\s+',' ',query).strip()
    if not 2<=len(q)<=100:raise ValueError('Search query must have 2–100 characters.')
    r=requests.get(API,params={'db':'healthTopics','term':q,'rettype':'topic','retmax':max(1,min(8,maximum)),'tool':'medpredict_x_atlas'},timeout=14)
    r.raise_for_status()
    if len(r.content)>1_500_000:raise ValueError('Atlas response too large.')
    return parse_medlineplus(r.text)


def atlas_queries(disease:str,mode:str) -> tuple[str,str]:
    if mode=='prevent':return f'{disease} prevention',"Prevention and risk reduction"
    return f'{disease} treatment',"Treatment and symptom management"
