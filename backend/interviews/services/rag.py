import re
from operator import itemgetter

from rank_bm25 import BM25Okapi

from ai_interviewer.runtime_config import RUNTIME
from interviews.models import CompanyDocument

TOKEN_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)
COMPANY_QUERY_MARKERS = [
    "your company",
    "your team",
    "your backend",
    "your frontend",
    "your stack",
    "you use",
    "do you use",
    "does your",
    "company use",
    "company work",
    "the role",
    "this role",
    "working there",
]


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def company_chunks():
    chunks = []
    for document in CompanyDocument.objects.all():
        paragraphs = [part.strip() for part in document.content.split("\n\n") if part.strip()]
        for paragraph in paragraphs:
            chunks.append((document.title, paragraph))
    return chunks


def candidate_asks_about_company(query):
    lowered = query.lower()
    return any(marker in lowered for marker in COMPANY_QUERY_MARKERS)


def retrieve_company_context(query):
    if not query.strip() or not candidate_asks_about_company(query):
        return ""

    chunks = company_chunks()
    if not chunks:
        return ""

    corpus = [tokenize(text) for _, text in chunks]
    index = BM25Okapi(corpus)
    scores = index.get_scores(tokenize(query))
    ranked = sorted(zip(scores, chunks), key=itemgetter(0), reverse=True)

    minimum_score = RUNTIME["rag"]["minimum_score"]
    max_chunks = RUNTIME["rag"]["max_chunks"]
    selected = []

    for score, chunk in ranked:
        if score < minimum_score or len(selected) >= max_chunks:
            continue
        title, text = chunk
        selected.append(f"{title}: {text}")

    return "\n\n".join(selected)
