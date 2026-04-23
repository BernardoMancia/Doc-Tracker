import re
from dataclasses import dataclass, field

from config.intelligence_matrix import IntelligenceMatrix


@dataclass
class RegexMatch:
    pattern_name: str
    value: str
    position: int
    context: str


@dataclass
class InspectionResult:
    cpf_matches: list[RegexMatch] = field(default_factory=list)
    cnpj_matches: list[RegexMatch] = field(default_factory=list)
    financial_matches: list[RegexMatch] = field(default_factory=list)
    email_matches: list[RegexMatch] = field(default_factory=list)
    phone_matches: list[RegexMatch] = field(default_factory=list)
    entity_matches: list[str] = field(default_factory=list)
    supplier_matches: list[str] = field(default_factory=list)
    people_matches: list[str] = field(default_factory=list)
    sensitive_term_matches: list[str] = field(default_factory=list)
    snippets: list[dict] = field(default_factory=list)

    @property
    def cpf_count(self) -> int:
        return len(self.cpf_matches)

    @property
    def cnpj_count(self) -> int:
        return len(self.cnpj_matches)

    @property
    def financial_count(self) -> int:
        return len(self.financial_matches)

    @property
    def has_findings(self) -> bool:
        return bool(
            self.cpf_matches
            or self.cnpj_matches
            or self.financial_matches
            or self.entity_matches
            or self.sensitive_term_matches
        )


class RegexEngine:

    PATTERNS = {
        "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
        "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
        "financial": re.compile(
            r"R\$\s*[\d.,]+(?:\.\d{3})*(?:,\d{2})?|\b\d{1,3}(?:\.\d{3})+,\d{2}\b"
        ),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\(?\d{2}\)?\s*\d{4,5}-?\d{4}"),
    }

    CONTEXT_RADIUS = 120

    def __init__(self, matrix: IntelligenceMatrix | None = None):
        self.matrix = matrix or IntelligenceMatrix()

    def _extract_context(self, text: str, start: int, end: int) -> str:
        ctx_start = max(0, start - self.CONTEXT_RADIUS)
        ctx_end = min(len(text), end + self.CONTEXT_RADIUS)
        context = text[ctx_start:ctx_end].replace("\n", " ").strip()
        if ctx_start > 0:
            context = "..." + context
        if ctx_end < len(text):
            context = context + "..."
        return context

    def _find_pattern_matches(self, text: str, pattern_name: str, pattern: re.Pattern) -> list[RegexMatch]:
        matches = []
        for m in pattern.finditer(text):
            context = self._extract_context(text, m.start(), m.end())
            matches.append(RegexMatch(pattern_name=pattern_name, value=m.group(), position=m.start(), context=context))
        return matches

    def _find_text_matches(self, text: str, terms: list[str]) -> list[str]:
        text_lower = text.lower()
        found = []
        for term in terms:
            if term.lower() in text_lower:
                found.append(term)
        return found

    def _build_snippets(self, text: str, all_matches: list[RegexMatch], max_snippets: int = 10) -> list[dict]:
        snippets = []
        seen_positions = set()
        for match in sorted(all_matches, key=lambda m: m.position)[:max_snippets]:
            bucket = match.position // 200
            if bucket in seen_positions:
                continue
            seen_positions.add(bucket)
            snippets.append({
                "type": match.pattern_name,
                "value_masked": self._mask_value(match.value, match.pattern_name),
                "context": self._mask_pii_in_context(match.context),
            })
        return snippets

    def _mask_value(self, value: str, pattern_name: str) -> str:
        if pattern_name == "cpf":
            clean = re.sub(r"[.\-]", "", value)
            if len(clean) == 11:
                return f"{clean[:3]}.***.*{clean[9]}{clean[10]}-{clean[9:11]}"
            return value[:4] + "***" + value[-3:]
        elif pattern_name == "cnpj":
            clean = re.sub(r"[.\-/]", "", value)
            if len(clean) == 14:
                return f"{clean[:2]}.***.***/****-{clean[12:]}"
            return value[:3] + "***" + value[-3:]
        elif pattern_name == "email":
            parts = value.split("@")
            if len(parts) == 2:
                user = parts[0]
                masked_user = user[0] + "***" + (user[-1] if len(user) > 1 else "")
                return f"{masked_user}@{parts[1]}"
        elif pattern_name == "phone":
            return value[:4] + "****" + value[-2:]
        return value[:3] + "***"

    def _mask_pii_in_context(self, context: str) -> str:
        result = context
        for cpf in self.PATTERNS["cpf"].finditer(result):
            result = result.replace(cpf.group(), self._mask_value(cpf.group(), "cpf"), 1)
        for cnpj in self.PATTERNS["cnpj"].finditer(result):
            result = result.replace(cnpj.group(), self._mask_value(cnpj.group(), "cnpj"), 1)
        for email in self.PATTERNS["email"].finditer(result):
            result = result.replace(email.group(), self._mask_value(email.group(), "email"), 1)
        return result

    def _validate_core_entity(self, text: str, entity_matches: list[str]) -> list[str]:
        if not entity_matches:
            return []
        text_lower = text.lower()
        for core in self.matrix.core_entities:
            if core.lower() in text_lower:
                return entity_matches
        return []

    def inspect(self, text: str) -> InspectionResult:
        if not text or len(text.strip()) < 10:
            return InspectionResult()

        result = InspectionResult()
        result.cpf_matches = self._find_pattern_matches(text, "cpf", self.PATTERNS["cpf"])
        result.cnpj_matches = self._find_pattern_matches(text, "cnpj", self.PATTERNS["cnpj"])
        result.financial_matches = self._find_pattern_matches(text, "financial", self.PATTERNS["financial"])
        result.email_matches = self._find_pattern_matches(text, "email", self.PATTERNS["email"])
        result.phone_matches = self._find_pattern_matches(text, "phone", self.PATTERNS["phone"])

        raw_entity_matches = self._find_text_matches(text, self.matrix.entities)
        result.entity_matches = self._validate_core_entity(text, raw_entity_matches)

        result.supplier_matches = self._find_text_matches(text, self.matrix.all_suppliers)
        result.people_matches = self._find_text_matches(text, self.matrix.key_people)
        result.sensitive_term_matches = self._find_text_matches(text, self.matrix.all_sensitive_terms)

        all_regex = result.cpf_matches + result.cnpj_matches + result.financial_matches + result.email_matches
        result.snippets = self._build_snippets(text, all_regex)
        return result

