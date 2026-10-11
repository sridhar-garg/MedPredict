"""Curated, attributable educational evidence retriever (no generative claims)."""
from __future__ import annotations



SOURCES = [
 {"topic":"chest x-ray", "title":"NIH ChestX-ray14 dataset and limitations",
  "url":"https://nihcc.app.box.com/v/ChestXray-NIHCC",
  "summary":"NIH ChestX-ray14 is a large chest-radiograph research dataset with report-derived findings. Weak labels and dataset shift limit clinical interpretation."},
 {"topic":"model evaluation", "title":"TRIPOD+AI prediction model reporting guidance",
  "url":"https://www.bmj.com/content/385/bmj-2023-078378",
  "summary":"Prediction studies should document data sources, target populations, sample selection, missing data, model development and rigorous evaluation."},
 {"topic":"medical imaging", "title":"CLAIM checklist for AI in medical imaging",
  "url":"https://pubs.rsna.org/doi/10.1148/ryai.240300",
  "summary":"Medical-imaging AI reports should make dataset selection, reference standards, model development and evaluation reproducible and transparent."},
 {"topic":"kidney", "title":"National Kidney Foundation eGFR information",
  "url":"https://www.kidney.org/kidney-topics/estimated-glomerular-filtration-rate-egfr",
  "summary":"Estimated glomerular filtration rate is an assessment of kidney filtration and is interpreted alongside other measurements and clinical context."},
 {"topic":"diabetes glucose", "title":"NIDDK diabetes tests and diagnosis",
  "url":"https://www.niddk.nih.gov/health-information/diabetes/overview/tests-diagnosis",
  "summary":"Diabetes screening uses validated blood tests such as A1C and plasma glucose; a single AI image prediction does not diagnose diabetes."},
 {"topic":"lab interoperability", "title":"HL7 FHIR Observation",
  "url":"https://hl7.org/fhir/observation.html",
  "summary":"FHIR Observation represents individual measurements and observations using codes, values and metadata, subject to implementation and profile requirements."},
 {"topic":"medical image segmentation", "title":"MONAI model zoo",
  "url":"https://github.com/Project-MONAI/model-zoo",
  "summary":"MONAI provides task-specific medical-imaging research model bundles, including segmentation models; using one requires matching anatomy and preprocessing."},
 {"topic":"benchmark", "title":"MedMNIST v2 lightweight imaging benchmarks",
  "url":"https://medmnist.com/",
  "summary":"MedMNIST packages benchmark biomedical classification datasets with defined labels and train, validation and test partitions."},
]


def find_evidence(question:str, top_k:int=4):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    docs=[s['topic']+' '+s['title']+' '+s['summary'] for s in SOURCES]
    vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2))
    matrix=vectorizer.fit_transform(docs+[question])
    scores=cosine_similarity(matrix[-1],matrix[:-1]).ravel()
    idx=scores.argsort()[::-1][:top_k]
    return [(SOURCES[int(i)],float(scores[i])) for i in idx if scores[i]>0]
