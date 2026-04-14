import json
from dataclasses import dataclass, field
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "entities.json"


def _load_entities_json() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _extract_from_json(data: list[dict]) -> dict:
    cnpjs = set()
    cpfs = set()
    fornecedores = set()
    emails = set()
    pessoas = set()
    entidades_extra = set()
    filial_enderecos = []

    for entity in data:
        if entity.get("razao_social"):
            entidades_extra.add(entity["razao_social"])

        for c in entity.get("todos_cnpjs", []):
            cnpjs.add(c)

        for c in entity.get("todos_cpfs", []):
            cpfs.add(c)

        for e in entity.get("emails", []):
            emails.add(e)

        for f in entity.get("fornecedores", []):
            if len(f) > 3:
                fornecedores.add(f)

        for admin in entity.get("administradores", []):
            if admin.get("nome"):
                pessoas.add(admin["nome"])
            if admin.get("cpf"):
                cpfs.add(admin["cpf"])

        for socio in entity.get("socios", []):
            if socio.get("nome"):
                entidades_extra.add(socio["nome"])
            if socio.get("cnpj"):
                cnpjs.add(socio["cnpj"])

        for filial in entity.get("filiais", []):
            if filial.get("cnpj"):
                cnpjs.add(filial["cnpj"])
            filial_enderecos.append(filial)

    return {
        "cnpjs": list(cnpjs),
        "cpfs": list(cpfs),
        "fornecedores": list(fornecedores),
        "emails": list(emails),
        "pessoas": list(pessoas),
        "entidades": list(entidades_extra),
        "filiais": filial_enderecos,
    }


@dataclass(frozen=True)
class IntelligenceMatrix:

    entities: list[str] = field(default_factory=lambda: [
        "Timac Agro",
        "Timac Agro Brasil",
        "TIMAC AGRO INDÚSTRIA E COMÉRCIO DE FERTILIZANTES LTDA",
        "Sulfabras",
        "Sulfabras Sulfatos do Brasil",
        "SULFABRÁS SULFATOS DO BRASIL LTDA",
        "Phosphea",
        "Phosphea Brasil",
        "PHOSPHEA BRASIL COMERCIO DE FOSFATOS LTDA",
        "Groupe Roullier",
        "Grupo Roullier",
        "Fipar Agro Internacional",
        "FIPAR AGRO INTERNATIONAL",
        "Agro Innovation International",
        "AGRO INNOVATION INTERNATIONAL",
        "Timab Industries S.A.S",
        "TIMAB INDUSTRIES S.A.S.",
        "Agrinter S.A.S",
        "AGRINTER S.A.S.",
    ])

    cnpjs: list[str] = field(default_factory=lambda: [
        "02.329.713/0001-29",
        "23.767.075/0001-06",
        "26.769.908/0001-58",
        "07.149.774/0001-28",
        "05.505.329/0001-28",
        "26.638.300/0001-94",
        "05.723.828/0001-91",
        "02329713000129",
        "23767075000106",
        "26769908000158",
    ])

    key_people: list[str] = field(default_factory=lambda: [
        "Daniel Clairton Schneider",
        "Diego Daniel Anaya",
    ])

    key_cpfs: list[str] = field(default_factory=lambda: [
        "495.677.300-59",
        "801.254.409-10",
    ])

    suppliers: list[str] = field(default_factory=lambda: [
        "Armac",
        "Armac Locação",
        "Pisani Plásticos",
        "OCP Brasil",
        "Tectextil Embalagens",
        "Ticket Soluções",
        "Cemig Geração",
        "Big Bag Embalagens",
        "3G Locações",
        "MA Locação",
    ])

    sensitive_terms_hr: list[str] = field(default_factory=lambda: [
        "colaborador",
        "funcionário",
        "holerite",
        "folha de pagamento",
        "rescisão",
        "banco de horas",
        "atestado médico",
        "salário",
        "admissão",
        "demissão",
    ])

    sensitive_terms_finance: list[str] = field(default_factory=lambda: [
        "nota fiscal",
        "fornecedor",
        "faturamento",
        "extrato",
        "contrato",
        "proposta comercial",
        "capital social",
        "balanço",
        "demonstrativo",
    ])

    sensitive_terms_it: list[str] = field(default_factory=lambda: [
        "senha",
        "password",
        "confidencial",
        "uso interno",
        "banco de dados",
        "acesso restrito",
        "privado",
        "interno",
        "restrito",
        "secret",
        "token",
        "api key",
    ])

    sensitive_terms_docs: list[str] = field(default_factory=lambda: [
        "ficha cadastral",
        "composição societária",
        "procuração",
        "ata de reunião",
        "contrato social",
        "alteração contratual",
        "certidão",
        "alvará",
    ])

    excluded_domains: list[str] = field(default_factory=lambda: [
        "timacagro.com.br",
        "timacagro.com",
        "phosphea.com",
        "roullier.com",
        "sulfabras.com.br",
    ])

    target_platforms: list[str] = field(default_factory=lambda: [
        "scribd.com",
        "slideshare.net",
        "issuu.com",
        "docdroid.net",
        "yumpu.com",
        "github.com",
        "gist.github.com",
        "pastebin.com",
        "trello.com",
        "drive.google.com",
        "dropbox.com",
        "mega.nz",
        "academia.edu",
        "calameo.com",
        "edocr.com",
        "pt.slideshare.net",
    ])

    file_extensions: list[str] = field(default_factory=lambda: [
        "pdf", "docx", "xlsx", "txt", "csv", "pptx",
    ])

    corporate_emails: list[str] = field(default_factory=list)
    extra_cnpjs: list[str] = field(default_factory=list)
    extra_suppliers: list[str] = field(default_factory=list)

    def __post_init__(self):
        json_data = _load_entities_json()
        if json_data:
            extracted = _extract_from_json(json_data)
            object.__setattr__(
                self,
                "extra_cnpjs",
                [c for c in extracted["cnpjs"] if c not in self.cnpjs],
            )
            object.__setattr__(
                self,
                "extra_suppliers",
                [s for s in extracted["fornecedores"] if s not in self.suppliers],
            )
            object.__setattr__(self, "corporate_emails", extracted["emails"])

            new_people = [p for p in extracted["pessoas"] if p not in self.key_people]
            if new_people:
                object.__setattr__(
                    self,
                    "key_people",
                    self.key_people + new_people,
                )

    @property
    def all_sensitive_terms(self) -> list[str]:
        return (
            self.sensitive_terms_hr
            + self.sensitive_terms_finance
            + self.sensitive_terms_it
            + self.sensitive_terms_docs
        )

    @property
    def all_cnpjs(self) -> list[str]:
        return self.cnpjs + self.extra_cnpjs

    @property
    def all_suppliers(self) -> list[str]:
        return self.suppliers + self.extra_suppliers

    @property
    def primary_identifiers(self) -> list[str]:
        return self.entities[:8] + self.cnpjs[:3]

    @property
    def exclusion_string(self) -> str:
        return " ".join(f"-site:{d}" for d in self.excluded_domains)
