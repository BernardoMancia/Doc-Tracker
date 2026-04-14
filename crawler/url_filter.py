import re
from urllib.parse import urlparse
from config.intelligence_matrix import IntelligenceMatrix


TLD_COUNTRY_MAP = {
    ".br": "BR", ".com.br": "BR", ".gov.br": "BR", ".org.br": "BR",
    ".pt": "PT", ".fr": "FR", ".es": "ES", ".de": "DE", ".it": "IT",
    ".uk": "GB", ".co.uk": "GB", ".us": "US", ".ca": "CA", ".mx": "MX",
    ".ar": "AR", ".cl": "CL", ".co": "CO", ".pe": "PE",
    ".cn": "CN", ".jp": "JP", ".kr": "KR", ".in": "IN",
    ".ru": "RU", ".au": "AU", ".nz": "NZ",
}

PT_MARKERS = [
    "ficha cadastral", "razão social", "cnpj", "cpf", "nota fiscal",
    "contrato social", "capital social", "administrador", "filial",
    "município", "endereço", "estado", "bairro", "cep",
    "inscrição estadual", "alvará", "certidão", "holerite",
    "funcionário", "colaborador", "faturamento", "fornecedor",
    "licitação", "edital", "pregão", "contrato", "aditivo",
]


def detect_country(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        for tld, country in sorted(TLD_COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
            if domain.endswith(tld):
                return country
    except Exception:
        pass
    return "INT"


def detect_language(text: str) -> str:
    if not text or len(text) < 50:
        return "unknown"
    sample = text[:3000].lower()
    pt_score = sum(1 for m in PT_MARKERS if m in sample)
    if pt_score >= 3:
        return "pt"
    en_markers = ["the ", " and ", " this ", " that ", " from ", " with ", "company", "address"]
    en_score = sum(1 for m in en_markers if m in sample)
    es_markers = [" y ", " de ", " empresa", " contrato", " dirección", " social"]
    es_score = sum(1 for m in es_markers if m in sample)
    fr_markers = [" et ", " les ", " des ", " une ", " dans ", "société", "adresse"]
    fr_score = sum(1 for m in fr_markers if m in sample)
    scores = {"pt": pt_score, "en": en_score, "es": es_score, "fr": fr_score}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "unknown"


class URLFilter:

    FILE_EXTENSIONS = {"pdf", "docx", "xlsx", "xls", "csv", "txt", "pptx", "doc"}
    PLATFORM_MAP = {
        "scribd.com": "Scribd",
        "slideshare.net": "SlideShare",
        "pt.slideshare.net": "SlideShare",
        "issuu.com": "Issuu",
        "docdroid.net": "DocDroid",
        "yumpu.com": "Yumpu",
        "github.com": "GitHub",
        "gist.github.com": "GitHub Gist",
        "pastebin.com": "Pastebin",
        "trello.com": "Trello",
        "drive.google.com": "Google Drive",
        "dropbox.com": "Dropbox",
        "mega.nz": "MEGA",
        "academia.edu": "Academia",
        "calameo.com": "Calameo",
        "edocr.com": "Edocr",
        "notion.site": "Notion",
        "gitlab.com": "GitLab",
        "bitbucket.org": "Bitbucket",
    }

    def __init__(self, matrix: IntelligenceMatrix | None = None):
        self.matrix = matrix or IntelligenceMatrix()
        self._excluded = set(d.lower() for d in self.matrix.excluded_domains)

    def is_valid(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            if any(domain.endswith(ex) for ex in self._excluded):
                return False
            if not parsed.scheme.startswith("http"):
                return False
            return True
        except Exception:
            return False

    def detect_file_type(self, url: str) -> str:
        path = urlparse(url).path.lower()
        for ext in self.FILE_EXTENSIONS:
            if path.endswith(f".{ext}"):
                return ext
        return "unknown"

    def detect_platform(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower().replace("www.", "")
            for pattern, name in self.PLATFORM_MAP.items():
                if pattern in domain:
                    return name
        except Exception:
            pass
        return "Other"
