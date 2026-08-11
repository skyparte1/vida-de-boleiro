import csv
import json
import re
import shutil
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from database import connect


BASE_DIR = Path(__file__).parent

# Pasta onde você colocará o dataset bruto de escudos baixado.
# Exemplo:
# source_club_logos/
#   arsenal.png
#   arsenal-fc.svg
#   real-madrid.png
#   ...
SOURCE_DIR = BASE_DIR / "source_club_logos"

# Destino final usado pelo site.
DEST_DIR = BASE_DIR / "static" / "club_logos"

# Arquivo opcional de aliases manuais.
ALIASES_FILE = BASE_DIR / "club_logo_aliases.json"

# Relatórios
UNMATCHED_FILE = BASE_DIR / "unmatched_clubs.csv"
MATCH_REPORT_FILE = BASE_DIR / "club_logo_match_report.csv"

# Extensões aceitas no dataset de origem.
ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}

# Limiar mínimo para aceitar um fuzzy match automaticamente.
# Aumente para ser mais conservador; diminua para aceitar mais matches.
FUZZY_THRESHOLD = 0.88


def normalize_name(text):
    """
    Normaliza nomes para comparação.

    Exemplo:
        'FC Bayern München' -> 'fc bayern munchen'
        'Paris Saint-Germain' -> 'paris saint germain'
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()

    replacements = {
        "&": " and ",
        "fc": " ",
        "cf": " ",
        "ac": " ",
        "afc": " ",
        "sc": " ",
        "club": " ",
        "clube": " ",
        "futebol": " ",
        "football": " ",
        "calcio": " ",
        "deportivo": " ",
        "sporting": " ",
        "association": " ",
    }

    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)

    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_aliases():
    if not ALIASES_FILE.exists():
        return {}

    with ALIASES_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    aliases = {}

    for key, value in raw.items():
        aliases[normalize_name(key)] = normalize_name(value)

    return aliases


def build_source_index():
    """
    Indexa todos os arquivos do dataset de escudos.
    A busca é recursiva, então SOURCE_DIR pode conter subpastas.
    """
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Pasta de origem não encontrada: {SOURCE_DIR}\n"
            "Crie a pasta e coloque nela o dataset de escudos."
        )

    index = []

    for file_path in SOURCE_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        normalized = normalize_name(file_path.stem)

        if not normalized:
            continue

        index.append(
            {
                "path": file_path,
                "normalized": normalized,
                "stem": file_path.stem,
            }
        )

    if not index:
        raise RuntimeError(
            f"Nenhum arquivo de imagem foi encontrado em {SOURCE_DIR}"
        )

    return index


def exact_match(target, source_index):
    for item in source_index:
        if item["normalized"] == target:
            return item, 1.0

    return None, 0.0


def fuzzy_match(target, source_index):
    best_item = None
    best_score = 0.0

    for item in source_index:
        score = SequenceMatcher(
            None,
            target,
            item["normalized"],
        ).ratio()

        if score > best_score:
            best_score = score
            best_item = item

    return best_item, best_score


def find_logo(club_name, aliases, source_index):
    """
    Ordem:
      1. alias manual;
      2. nome exato normalizado;
      3. fuzzy matching.
    """
    club_normalized = normalize_name(club_name)

    alias_target = aliases.get(club_normalized)

    if alias_target:
        item, score = exact_match(alias_target, source_index)

        if item:
            return item, 1.0, "alias"

        item, score = fuzzy_match(alias_target, source_index)

        if item and score >= FUZZY_THRESHOLD:
            return item, score, "alias_fuzzy"

    item, score = exact_match(club_normalized, source_index)

    if item:
        return item, 1.0, "exact"

    item, score = fuzzy_match(club_normalized, source_index)

    if item and score >= FUZZY_THRESHOLD:
        return item, score, "fuzzy"

    return None, score, "unmatched"


def copy_logo(source_path, country_code, club_name):
    """
    Copia o escudo para:
        static/club_logos/<PAIS>/<slug>.<ext>

    Mantém a extensão original.
    """
    country_dir = DEST_DIR / country_code
    country_dir.mkdir(parents=True, exist_ok=True)

    extension = source_path.suffix.lower()
    filename = f"{slugify(club_name)}{extension}"

    destination = country_dir / filename

    shutil.copy2(source_path, destination)

    return destination


def database_logo_path(destination):
    """
    Converte o caminho físico em caminho relativo ao diretório club_logos.
    """
    return destination.relative_to(DEST_DIR).as_posix()


def write_unmatched(rows):
    with UNMATCHED_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "club_id",
                "club",
                "country",
                "country_code",
                "best_candidate",
                "score",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)


def write_match_report(rows):
    with MATCH_REPORT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "club_id",
                "club",
                "country",
                "country_code",
                "source_file",
                "destination",
                "method",
                "score",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    aliases = load_aliases()
    source_index = build_source_index()

    print(f"Escudos encontrados no dataset: {len(source_index)}")
    print(f"Aliases carregados: {len(aliases)}")
    print()

    with connect() as connection:
        clubs = connection.execute(
            """
            SELECT
                clubs.id,
                clubs.name,
                countries.name AS country,
                countries.code AS country_code
            FROM clubs
            JOIN countries
                ON countries.id = clubs.country_id
            ORDER BY countries.code, clubs.name
            """
        ).fetchall()

        matched_rows = []
        unmatched_rows = []

        matched = 0
        unmatched = 0

        for club in clubs:
            item, score, method = find_logo(
                club["name"],
                aliases,
                source_index,
            )

            if item is None:
                unmatched += 1

                candidate, candidate_score = fuzzy_match(
                    normalize_name(club["name"]),
                    source_index,
                )

                unmatched_rows.append(
                    {
                        "club_id": club["id"],
                        "club": club["name"],
                        "country": club["country"],
                        "country_code": club["country_code"],
                        "best_candidate": (
                            candidate["stem"] if candidate else ""
                        ),
                        "score": (
                            f"{candidate_score:.3f}"
                            if candidate
                            else ""
                        ),
                    }
                )

                print(
                    f"[NÃO ENCONTRADO] "
                    f"{club['country_code']} | {club['name']}"
                )

                continue

            destination = copy_logo(
                item["path"],
                club["country_code"],
                club["name"],
            )

            relative_logo = database_logo_path(destination)

            connection.execute(
                """
                UPDATE clubs
                SET logo = ?
                WHERE id = ?
                """,
                (
                    relative_logo,
                    club["id"],
                ),
            )

            matched += 1

            matched_rows.append(
                {
                    "club_id": club["id"],
                    "club": club["name"],
                    "country": club["country"],
                    "country_code": club["country_code"],
                    "source_file": str(item["path"]),
                    "destination": relative_logo,
                    "method": method,
                    "score": f"{score:.3f}",
                }
            )

            print(
                f"[OK] {club['country_code']} | "
                f"{club['name']} -> {relative_logo} "
                f"({method}, {score:.3f})"
            )

    write_unmatched(unmatched_rows)
    write_match_report(matched_rows)

    print()
    print("=" * 60)
    print("IMPORTAÇÃO CONCLUÍDA")
    print("=" * 60)
    print(f"Clubes no banco: {matched + unmatched}")
    print(f"Escudos encontrados: {matched}")
    print(f"Não encontrados: {unmatched}")
    print()
    print(f"Relatório de matches: {MATCH_REPORT_FILE}")
    print(f"Não encontrados: {UNMATCHED_FILE}")

    if unmatched:
        print()
        print(
            "Revise unmatched_clubs.csv e adicione aliases em "
            "club_logo_aliases.json para os casos restantes."
        )


if __name__ == "__main__":
    main()
