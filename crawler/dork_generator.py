from config.intelligence_matrix import IntelligenceMatrix


class DorkGenerator:

    def __init__(self, matrix: IntelligenceMatrix | None = None):
        self.matrix = matrix or IntelligenceMatrix()

    def _or_group(self, items: list[str], max_items: int = 5) -> list[str]:
        groups = []
        for i in range(0, len(items), max_items):
            chunk = items[i : i + max_items]
            inner = " OR ".join(f'"{item}"' for item in chunk)
            groups.append(f"({inner})")
        return groups

    def _entity_block(self, max_items: int = 6) -> str:
        items = self.matrix.core_entities[:max_items]
        return "(" + " OR ".join(f'"{e}"' for e in items) + ")"

    def generate_entity_dorks(self) -> list[str]:
        dorks = []
        entity = self._entity_block()
        exclusion = self.matrix.exclusion_string
        sensitive_groups = self._or_group(self.matrix.all_sensitive_terms, 6)

        for sg in sensitive_groups:
            for ext in ["pdf", "docx", "xlsx"]:
                dorks.append(f"{entity} {sg} ext:{ext} {exclusion}")

        return dorks

    def generate_platform_dorks(self) -> list[str]:
        dorks = []
        entity = self._entity_block(4)

        for platform in self.matrix.target_platforms:
            dorks.append(f"site:{platform} {entity}")

        return dorks

    def generate_scribd_deep(self) -> list[str]:
        dorks = []
        names = ["Timac Agro", "Sulfabras", "Phosphea", "Roullier"]

        for name in names:
            dorks.append(f'site:scribd.com "{name}"')
            dorks.append(f'site:pt.scribd.com "{name}"')

        dorks.append('site:scribd.com ("Timac Agro" OR "Sulfabras" OR "Phosphea") ("confidencial" OR "interno")')
        dorks.append('site:slideshare.net ("Timac Agro" OR "Sulfabras" OR "Phosphea")')
        dorks.append('site:issuu.com ("Timac Agro" OR "Sulfabras")')
        dorks.append('site:yumpu.com ("Timac Agro" OR "Sulfabras")')
        dorks.append('site:calameo.com ("Timac Agro" OR "Sulfabras")')
        dorks.append('site:academia.edu ("Timac Agro" OR "Sulfabras" OR "Roullier")')

        return dorks

    def generate_author_dorks(self) -> list[str]:
        dorks = []
        exclusion = self.matrix.exclusion_string

        for person in self.matrix.key_people:
            dorks.append(f'"{person}" {exclusion}')
            dorks.append(f'"{person}" ("Timac" OR "Sulfabras" OR "Phosphea")')

        entity = self._entity_block(4)
        dorks.append(f'{entity} ("uploaded by" OR "publicado por" OR "author" OR "autor") {exclusion}')
        dorks.append(f'{entity} ("published by" OR "enviado por" OR "criado por") {exclusion}')

        return dorks

    def generate_private_project_dorks(self) -> list[str]:
        dorks = []
        entity = self._entity_block(4)
        exclusion = self.matrix.exclusion_string

        dorks.append(f'{entity} ("confidencial" OR "privado" OR "uso interno" OR "restrito") {exclusion}')
        dorks.append(f'{entity} ("projeto" OR "project") ("interno" OR "confidencial") {exclusion}')
        dorks.append(f'{entity} ("contrato" OR "proposta" OR "licitação") ext:pdf {exclusion}')
        dorks.append(f'{entity} ("ata de reunião" OR "minuta" OR "procuração") {exclusion}')
        dorks.append(f'{entity} ("ficha cadastral" OR "composição societária" OR "contrato social") {exclusion}')

        dorks.append(f'site:github.com ("timac" OR "sulfabras" OR "phosphea" OR "roullier")')
        dorks.append(f'site:gitlab.com ("timac" OR "sulfabras" OR "phosphea")')
        dorks.append(f'site:bitbucket.org ("timac" OR "sulfabras" OR "phosphea")')
        dorks.append(f'site:trello.com ("Timac Agro" OR "Sulfabras")')
        dorks.append(f'site:notion.site ("Timac Agro" OR "Sulfabras")')

        return dorks

    def generate_cnpj_dorks(self) -> list[str]:
        dorks = []
        exclusion = self.matrix.exclusion_string
        main_cnpjs = self.matrix.cnpjs[:3]

        for cnpj in main_cnpjs:
            dorks.append(f'"{cnpj}" {exclusion}')

        all_cnpjs = " OR ".join(f'"{c}"' for c in main_cnpjs)
        dorks.append(f'({all_cnpjs}) ext:pdf {exclusion}')
        dorks.append(f'({all_cnpjs}) ext:xlsx {exclusion}')

        return dorks

    def generate_supplier_dorks(self) -> list[str]:
        dorks = []
        entity = self._entity_block(4)
        all_suppliers = self.matrix.all_suppliers[:12]
        supplier_block = "(" + " OR ".join(f'"{s}"' for s in all_suppliers[:6]) + ")"
        exclusion = self.matrix.exclusion_string

        for ext in ["pdf", "xlsx"]:
            dorks.append(f"{entity} {supplier_block} ext:{ext} {exclusion}")

        return dorks

    def generate_cpf_dorks(self) -> list[str]:
        dorks = []
        exclusion = self.matrix.exclusion_string

        for cpf in self.matrix.key_cpfs:
            dorks.append(f'"{cpf}" {exclusion}')

        return dorks

    def generate_all(self) -> list[str]:
        all_dorks = []
        all_dorks.extend(self.generate_entity_dorks())
        all_dorks.extend(self.generate_platform_dorks())
        all_dorks.extend(self.generate_scribd_deep())
        all_dorks.extend(self.generate_author_dorks())
        all_dorks.extend(self.generate_private_project_dorks())
        all_dorks.extend(self.generate_cnpj_dorks())
        all_dorks.extend(self.generate_supplier_dorks())
        all_dorks.extend(self.generate_cpf_dorks())

        seen = set()
        unique = []
        for d in all_dorks:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        return unique
