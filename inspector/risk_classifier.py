from dataclasses import dataclass
from inspector.regex_engine import InspectionResult
from config.intelligence_matrix import IntelligenceMatrix


@dataclass
class RiskAssessment:
    level: str
    score: int
    category: str
    reasons: list[str]


class RiskClassifier:

    TARGET_CNPJS_CLEAN = {"02329713000129", "23767075000106", "26769908000158"}

    def __init__(self, matrix: IntelligenceMatrix | None = None):
        self.matrix = matrix or IntelligenceMatrix()

    def _has_target_cnpj(self, result: InspectionResult) -> bool:
        import re
        for match in result.cnpj_matches:
            clean = re.sub(r"[.\-/]", "", match.value)
            if clean in self.TARGET_CNPJS_CLEAN:
                return True
        return False

    def _determine_category(self, result: InspectionResult) -> str:
        hr_terms = set(self.matrix.sensitive_terms_hr)
        finance_terms = set(self.matrix.sensitive_terms_finance)
        it_terms = set(self.matrix.sensitive_terms_it)
        matched = set(t.lower() for t in result.sensitive_term_matches)
        hr_hits = len(matched & set(t.lower() for t in hr_terms))
        fin_hits = len(matched & set(t.lower() for t in finance_terms))
        it_hits = len(matched & set(t.lower() for t in it_terms))

        if it_hits > 0 and (result.cpf_count > 0 or self._has_target_cnpj(result)):
            return "ti_security"
        if hr_hits >= fin_hits and hr_hits > 0:
            return "rh"
        if fin_hits > 0:
            return "financeiro"
        if it_hits > 0:
            return "ti"
        if result.cpf_count > 0:
            return "dados_pessoais"
        if result.cnpj_count > 0:
            return "corporativo"
        return "general"

    def classify(self, result: InspectionResult) -> RiskAssessment:
        score = 0
        reasons = []
        has_entity = bool(result.entity_matches)
        has_target_cnpj = self._has_target_cnpj(result)

        if has_target_cnpj:
            score += 25
            reasons.append("CNPJ alvo detectado")
        if has_entity:
            score += 15
            reasons.append(f"Entidade: {', '.join(result.entity_matches[:3])}")
        if result.cpf_count > 0:
            score += min(result.cpf_count * 5, 25)
            reasons.append(f"{result.cpf_count} CPF(s) detectado(s)")
        if result.cnpj_count > 0 and not has_target_cnpj:
            score += min(result.cnpj_count * 3, 10)
            reasons.append(f"{result.cnpj_count} CNPJ(s) detectado(s)")
        if result.financial_count > 0:
            score += min(result.financial_count * 2, 10)
            reasons.append(f"{result.financial_count} valor(es) financeiro(s)")
        if result.people_matches:
            score += 10
            reasons.append(f"Pessoa-chave: {', '.join(result.people_matches)}")
        if result.supplier_matches:
            score += 5
            reasons.append(f"Fornecedor: {', '.join(result.supplier_matches[:2])}")

        it_terms = set(t.lower() for t in self.matrix.sensitive_terms_it)
        matched_it = [t for t in result.sensitive_term_matches if t.lower() in it_terms]
        if matched_it:
            score += 15
            reasons.append(f"Termos TI: {', '.join(matched_it[:3])}")

        hr_terms = set(t.lower() for t in self.matrix.sensitive_terms_hr)
        matched_hr = [t for t in result.sensitive_term_matches if t.lower() in hr_terms]
        if matched_hr:
            score += 10
            reasons.append(f"Termos RH: {', '.join(matched_hr[:3])}")

        score = min(score, 100)

        if score >= 80:
            level = "critical"
        elif score >= 60:
            level = "high"
        elif score >= 30:
            level = "medium"
        else:
            level = "low"

        return RiskAssessment(level=level, score=score, category=self._determine_category(result), reasons=reasons)
