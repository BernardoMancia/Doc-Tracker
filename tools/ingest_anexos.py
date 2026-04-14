import json
import re
import shutil
import sys
from pathlib import Path

import fitz


BASE_DIR = Path(__file__).resolve().parent.parent
ANEXOS_DIR = BASE_DIR / "anexos"
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "entities.json"


def extract_field(text: str, label: str, fallback: str = "") -> str:
    pattern = rf"{re.escape(label)}[:\s]*(.+?)(?:\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else fallback


def extract_all_cnpjs(text: str) -> list[str]:
    raw = re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", text)
    seen = set()
    result = []
    for c in raw:
        clean = re.sub(r"[.\-/]", "", c)
        if len(clean) == 14 and clean not in seen:
            seen.add(clean)
            formatted = f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:]}"
            result.append(formatted)
    return result


def extract_all_cpfs(text: str) -> list[str]:
    raw = re.findall(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", text)
    seen = set()
    result = []
    for c in raw:
        clean = re.sub(r"[.\-]", "", c)
        if len(clean) == 11 and clean not in seen:
            seen.add(clean)
            formatted = f"{clean[:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:]}"
            result.append(formatted)
    return result


def extract_emails(text: str) -> list[str]:
    return list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))


def extract_phones(text: str) -> list[str]:
    raw = re.findall(r"\+?\d{2}\s*\d{2}\s*\d{4,5}[\s-]?\d{4}", text)
    return list(set(raw))


def extract_socios(text: str) -> list[dict]:
    socios = []
    blocks = re.split(r"S[ÓO]CIO\s*\d+\s*:", text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        nome = extract_field(block, "NOME")
        participacao = extract_field(block, "PARTICIPAÇÃO") or extract_field(block, "PARTICIPACAO")
        cnpj = extract_field(block, "CNPJ")
        if nome:
            socios.append({
                "nome": nome,
                "participacao": participacao,
                "cnpj": cnpj,
            })
    return socios


def extract_administradores(text: str) -> list[dict]:
    admins = []
    for match in re.finditer(
        r"ADMINISTRADOR[:\s]*([^\n]+)\s*CPF[:\s]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})",
        text,
        re.IGNORECASE,
    ):
        admins.append({
            "nome": match.group(1).strip(),
            "cpf": match.group(2).strip(),
        })
    return admins


def extract_fornecedores(text: str) -> list[str]:
    fornecedores = []
    section = re.search(
        r"(?:Principais?\s*)?Fornecedore?s.*?\n(.*?)(?:FICHA\s*CADASTRAL|Refer[êe]ncias|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if section:
        lines = section.group(1).strip().split("\n")
        for line in lines:
            clean = line.strip()
            if (
                clean
                and len(clean) > 3
                and not re.match(r"^(FORNECEDOR|ESTADO|CIDADE|BANCO|AG[ÊE]NCIA)", clean, re.IGNORECASE)
            ):
                fornecedores.append(clean)
    return fornecedores


def extract_filiais(text: str) -> list[dict]:
    filiais = []
    cnpj_blocks = re.split(r"CNPJ/MF[:\s]*", text, flags=re.IGNORECASE)
    for block in cnpj_blocks[1:]:
        cnpj_match = re.match(r"(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})", block)
        if not cnpj_match:
            continue
        cnpj = cnpj_match.group(1)
        cidade = extract_field(block, "CIDADE")
        estado = extract_field(block, "ESTADO")
        endereco = extract_field(block, "ENDEREÇO") or extract_field(block, "ENDERECO")
        filiais.append({
            "cnpj": cnpj,
            "cidade": cidade,
            "estado": estado,
            "endereco": endereco,
        })
    return filiais


def extract_ref_bancarias(text: str) -> list[dict]:
    refs = []
    section = re.search(
        r"Refer[êe]ncias\s*Banc[aá]rias.*?\n(.*?)(?:Refer[êe]ncias\s*Comerciais|Principais|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if section:
        banco_matches = re.findall(
            r"(ITA[ÚU]|BRADESCO|SANTANDER|BANCO DO BRASIL|BB|CAIXA|SAFRA|BTG)[\s\S]*?(\d{4})",
            section.group(1),
            re.IGNORECASE,
        )
        for banco, agencia in banco_matches:
            refs.append({"banco": banco.strip(), "agencia": agencia.strip()})
    return refs


def process_pdf(pdf_path: Path) -> dict:
    doc = fitz.open(str(pdf_path))
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()

    razao_social = extract_field(full_text, "RAZÃO SOCIAL") or extract_field(full_text, "RAZAO SOCIAL")
    cnpj_principal = extract_field(full_text, "CNPJ")
    ie = extract_field(full_text, "I.E.") or extract_field(full_text, "I.E")
    fundacao = extract_field(full_text, "DATA DA FUNDAÇÃO") or extract_field(full_text, "DATA DA FUNDACAO")
    capital_social = extract_field(full_text, "CAPITAL SOCIAL")
    ramo = extract_field(full_text, "RAMO DE ATIVIDADE")
    endereco = extract_field(full_text, "ENDEREÇO") or extract_field(full_text, "ENDERECO")
    bairro = extract_field(full_text, "BAIRRO")
    cidade = extract_field(full_text, "CIDADE")
    cep = extract_field(full_text, "CEP")
    estado = extract_field(full_text, "ESTADO")
    website = extract_field(full_text, "WEBSITE")
    telefone = extract_field(full_text, "TELEFONE")

    return {
        "source_file": pdf_path.name,
        "razao_social": razao_social,
        "cnpj_principal": cnpj_principal,
        "inscricao_estadual": ie,
        "data_fundacao": fundacao,
        "capital_social": capital_social,
        "ramo_atividade": ramo,
        "sede": {
            "endereco": endereco,
            "bairro": bairro,
            "cidade": cidade,
            "cep": cep,
            "estado": estado,
        },
        "website": website,
        "telefone": telefone,
        "socios": extract_socios(full_text),
        "administradores": extract_administradores(full_text),
        "filiais": extract_filiais(full_text),
        "todos_cnpjs": extract_all_cnpjs(full_text),
        "todos_cpfs": extract_all_cpfs(full_text),
        "emails": extract_emails(full_text),
        "telefones": extract_phones(full_text),
        "fornecedores": extract_fornecedores(full_text),
        "referencias_bancarias": extract_ref_bancarias(full_text),
    }


def main():
    if not ANEXOS_DIR.exists():
        print(f"[!] Pasta '{ANEXOS_DIR}' não encontrada.")
        sys.exit(1)

    pdfs = list(ANEXOS_DIR.glob("*.pdf"))
    if not pdfs:
        print("[!] Nenhum PDF encontrado na pasta anexos/")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    entities = []
    for pdf in pdfs:
        print(f"[*] Processando: {pdf.name}")
        entity = process_pdf(pdf)
        entities.append(entity)
        print(f"    -> {entity['razao_social']}")
        print(f"    -> {len(entity['todos_cnpjs'])} CNPJs, {len(entity['todos_cpfs'])} CPFs")
        print(f"    -> {len(entity['filiais'])} filiais, {len(entity['fornecedores'])} fornecedores")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Dados salvos em: {OUTPUT_FILE}")
    print(f"[+] {len(entities)} entidades processadas")

    for pdf in pdfs:
        pdf.unlink()
        print(f"[-] Deletado: {pdf.name}")

    if ANEXOS_DIR.exists() and not list(ANEXOS_DIR.iterdir()):
        ANEXOS_DIR.rmdir()
        print(f"[-] Pasta 'anexos/' removida")

    print("\n[✓] Ingestão completa!")


if __name__ == "__main__":
    main()
