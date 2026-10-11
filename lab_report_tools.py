"""Research report extraction. OCR output must be verified by a human.
No cloud OCR, no report database, no diagnosis.
"""
from __future__ import annotations
from io import BytesIO
import re
from datetime import date
from uuid import uuid4

TESTS = {
 "Haemoglobin": {"aliases": [r"haemoglobin", r"hemoglobin", r"\bhgb\b", r"\bhb\b"], "unit": "g/dL", "loinc":"718-7"},
 "Creatinine": {"aliases": [r"creatinine(?:\s*\(serum\))?", r"serum\s+creatinine"], "unit":"mg/dL", "loinc":"2160-0"},
 "LDL cholesterol": {"aliases": [r"\bldl(?:\s+cholesterol)?\b"], "unit":"mg/dL", "loinc":"13457-7"},
 "Total cholesterol": {"aliases": [r"total\s+cholesterol", r"\bcholesterol\s+total"], "unit":"mg/dL", "loinc":"2093-3"},
 "Glucose": {"aliases": [r"(?:fasting\s+)?(?:blood\s+)?glucose", r"blood\s+sugar"], "unit":"mg/dL", "loinc":"2345-7"},
 "ALT": {"aliases": [r"\balt\b", r"\bsgpt\b"], "unit":"U/L", "loinc":"1742-6"},
 "AST": {"aliases": [r"\bast\b", r"\bsgot\b"], "unit":"U/L", "loinc":"1920-8"},
 "Platelets": {"aliases": [r"platelet(?:s|\s+count)?"], "unit":"10^3/uL", "loinc":"777-3"},
}

NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])(-?\d{1,5}(?:[,.]\d{1,3})?)")
UNIT_RE = re.compile(r"(?i)(mg\s*/\s*d[lL]|g\s*/\s*d[lL]|u\s*/\s*[lL]|IU\s*/\s*[lL]|10\^?3\s*/\s*[uµ]L|mmol\s*/\s*[lL])")


def candidates(text):
    """Returns candidate values with source snippets; never infer units silently."""
    found=[]
    for line_idx,line in enumerate(text.splitlines()):
        compact=' '.join(line.strip().split())
        if not compact or len(compact)>400:continue
        for name, spec in TESTS.items():
            match=next((m for a in spec['aliases'] if (m:=re.search(a,compact,re.I))),None)
            if not match:continue

            following=compact[match.end():]
            num=NUMBER_RE.search(following)
            if num is None:continue
            raw=num.group(1).replace(",", "")
            try: value=float(raw)
            except ValueError: continue
            if not (0 <= value <= 20000):continue
            unit_match=UNIT_RE.search(following[num.end():])
            detected=unit_match.group(0).replace(" ","") if unit_match else "Unknown"
            normalized=detected.lower().replace("µ","u")
            expected=spec['unit'].lower().replace(" ","")
            approved=normalized==expected or (name in ('AST','ALT') and normalized in ('u/l','iu/l'))
            found.append({"line":line_idx+1,"test":name,"candidate_value":value,
                          "unit_read":detected,"expected_unit":spec['unit'],
                          "unit_matches":approved,"source_excerpt":compact[:180]})
    return found


def to_fhir_observations(rows, date_str=None):
    """FHIR-like observation Bundle with study labels only. Not a validated interoperability claim."""
    observed_date = date_str or date.today().isoformat()
    entries=[]
    for row in rows:
        spec=TESTS.get(row.get('test'))
        if not spec or not row.get('unit_matches') or not row.get('human_verified'):continue
        obs={"resourceType":"Observation","id":str(uuid4()),"status":"final",
             "code":{"coding":[{"system":"http://loinc.org","code":spec['loinc'],"display":row['test']}]},
             "effectiveDateTime":observed_date,
             "valueQuantity":{"value":float(row['candidate_value']),"unit":spec['unit']},
             "note":[{"text":"Patient-verified transcription from a research prototype; not an authoritative EHR result."}]}
        entries.append({"resource":obs})
    return {"resourceType":"Bundle","type":"collection","entry":entries}


def pdf_or_image_to_text(data: bytes, filename: str) -> str:
    if len(data)>20*1024*1024:raise ValueError("File is over 20 MB")
    if filename.lower().endswith('.pdf'):
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(data))
        if len(reader.pages)>12:raise ValueError("Upload 12 or fewer pages")
        text='\n'.join((p.extract_text() or '') for p in reader.pages)
        if len(text.strip())>30:return text
        import fitz
        pdf=fitz.open(stream=data,filetype='pdf')
        try:
            import pytesseract
            from PIL import Image
            pages=[]
            for page in pdf:
                pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),colorspace=fitz.csRGB,alpha=False)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                pages.append(pytesseract.image_to_string(image))
            return '\n'.join(pages)
        finally:pdf.close()
    from PIL import Image
    import pytesseract
    return pytesseract.image_to_string(Image.open(BytesIO(data)))
