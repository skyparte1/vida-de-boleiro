import csv
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from database import connect


BASE_DIR = Path(__file__).parent

# Estrutura esperada:
# source_club_logos/
# ├── BRA/
# ├── ENG/
# ├── ESP/
# ├── ITA/
# ├── GER/
# ├── FRA/
# ├── POR/
# ├── NED/
# ├── ARG/
# └── BEL/
SOURCE_DIR = BASE_DIR / "source_club_logos"

# Destino final usado pelo site.
DEST_DIR = BASE_DIR / "static" / "club_logos"

# Aliases manuais opcionais.
ALIASES_FILE = BASE_DIR / "club_logo_aliases.json"

# Relatórios.
UNMATCHED_FILE = BASE_DIR / "unmatched_clubs.csv"
MATCH_REPORT_FILE = BASE_DIR / "club_logo_match_report.csv"
COUNTRY_REPORT_FILE = BASE_DIR / "club_logo_country_report.csv"

# Extensões aceitas.
ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}

# Limiar de aceitação automática do fuzzy match.
FUZZY_THRESHOLD = 0.88

# Se True, sobrescreve escudos já existentes no destino.
OVERWRITE_EXISTING = False


def normalize_name(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()

    # Remoção leve de termos muito comuns.
    # Não removemos palavras como "sporting" ou "deportivo",
    # pois podem ser importantes para distinguir clubes.
    removable_words = {
        "fc",
        "cf",
        "ac",
        "afc",
        "sc",
        "club",
        "clube",
        "football",
        "futebol",
    }

    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    tokens = [
        token
        for token in text.split()
        if token not in removable_words
    ]

    return " ".join(tokens).strip()


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_aliases():
    """
    Formatos aceitos:

    {
        "FC Bayern München": "Bayern Munich"
    }

    ou, para maior precisão por país:

    {
        "GER|FC Bayern München": "Bayern Munich",
        "ARG|Racing Club": "Racing Club de Avellaneda"
    }

    O alias específico por país tem prioridade.
    """
    if not ALIASES_FILE.exists():
        return {}

    with ALIASES_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    aliases = {}

    for key, value in raw.items():
        if "|" in key:
            country_code, club_name = key.split("|", 1)
            normalized_key = (
                country_code.strip().upper(),
                normalize_name(club_name),
            )
        else:
            normalized_key = (
                None,
                normalize_name(key),
            )

        aliases[normalized_key] = normalize_name(value)

    return aliases


def get_alias(aliases, country_code, club_name):
    normalized_club = normalize_name(club_name)

    specific = aliases.get((country_code, normalized_club))
    if specific:
        return specific

    return aliases.get((None, normalized_club))


def build_country_source_index(country_code):
    """
    Indexa SOMENTE a pasta do país correspondente.

    Exemplo:
        source_club_logos/BRA/
    """
    country_dir = SOURCE_DIR / country_code

    if not country_dir.exists():
        return []

    index = []

    for file_path in country_dir.rglob("*"):
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

    return index


def exact_match(target, source_index):
    matches = [
        item
        for item in source_index
        if item["normalized"] == target
    ]

    if len(matches) == 1:
        return matches[0], 1.0

    # Se houver múltiplos arquivos com exatamente o mesmo nome,
    # não escolhemos arbitrariamente.
    return None, 0.0


def fuzzy_match(target, source_index):
    best_item = None
    best_score = 0.0
    second_best_score = 0.0

    for item in source_index:
        score = SequenceMatcher(
            None,
            target,
            item["normalized"],
        ).ratio()

        if score > best_score:
            second_best_score = best_score
            best_score = score
            best_item = item
        elif score > second_best_score:
            second_best_score = score

    return best_item, best_score, second_best_score


def find_logo(club_name, country_code, aliases, source_index):
    """
    Ordem:
      1. alias específico/manual;
      2. nome exato;
      3. fuzzy match.

    O fuzzy match só é aceito se:
      - passar o limiar;
      - não houver outro candidato quase empatado.
    """
    club_normalized = normalize_name(club_name)
    alias_target = get_alias(
        aliases,
        country_code,
        club_name,
    )

    if alias_target:
        item, score = exact_match(
            alias_target,
            source_index,
        )

        if item:
            return item, 1.0, "alias"

        item, score, second = fuzzy_match(
            alias_target,
            source_index,
        )

        if (
            item
            and score >= FUZZY_THRESHOLD
            and (score - second) >= 0.04
        ):
            return item, score, "alias_fuzzy"

    item, score = exact_match(
        club_normalized,
        source_index,
    )

    if item:
        return item, 1.0, "exact"

    item, score, second = fuzzy_match(
        club_normalized,
        source_index,
    )

    if (
        item
        and score >= FUZZY_THRESHOLD
        and (score - second) >= 0.04
    ):
        return item, score, "fuzzy"

    return None, score, "unmatched"


def copy_logo(source_path, country_code, club_name):
    country_dir = DEST_DIR / country_code
    country_dir.mkdir(parents=True, exist_ok=True)

    extension = source_path.suffix.lower()
    filename = f"{slugify(club_name)}{extension}"
    destination = country_dir / filename

    if destination.exists() and not OVERWRITE_EXISTING:
        return destination

    shutil.copy2(source_path, destination)

    return destination


def database_logo_path(destination):
    return destination.relative_to(DEST_DIR).as_posix()


def write_csv(path, rows, fieldnames):
    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Pasta não encontrada: {SOURCE_DIR}\n"
            "Crie source_club_logos e dentro dela use pastas "
            "como BRA, ENG, ESP, ARG etc."
        )

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    aliases = load_aliases()

    with connect() as connection:
        clubs = connection.execute(
            """
            SELECT
                clubs.id,
                clubs.name,
                clubs.logo,
                countries.name AS country,
                countries.code AS country_code
            FROM clubs
            JOIN countries
                ON countries.id = clubs.country_id
            ORDER BY countries.code, clubs.name
            """
        ).fetchall()

        clubs_by_country = defaultdict(list)

        for club in clubs:
            clubs_by_country[club["country_code"]].append(club)

        matched_rows = []
        unmatched_rows = []
        country_summary = []

        total_matched = 0
        total_unmatched = 0

        for country_code in sorted(clubs_by_country):
            country_clubs = clubs_by_country[country_code]
            source_index = build_country_source_index(
                country_code
            )

            country_matched = 0
            country_unmatched = 0

            print()
            print("=" * 70)
            print(
                f"{country_code} | "
                f"{country_clubs[0]['country']} | "
                f"{len(country_clubs)} clubes | "
                f"{len(source_index)} imagens disponíveis"
            )
            print("=" * 70)

            if not source_index:
                print(
                    f"[SEM DATASET] Nenhuma imagem em "
                    f"source_club_logos/{country_code}/"
                )

                for club in country_clubs:
                    unmatched_rows.append(
                        {
                            "club_id": club["id"],
                            "club": club["name"],
                            "country": club["country"],
                            "country_code": country_code,
                            "best_candidate": "",
                            "score": "",
                            "reason": "country_folder_empty_or_missing",
                        }
                    )

                country_unmatched = len(country_clubs)
                total_unmatched += country_unmatched

                country_summary.append(
                    {
                        "country_code": country_code,
                        "country": country_clubs[0]["country"],
                        "clubs": len(country_clubs),
                        "source_images": 0,
                        "matched": 0,
                        "unmatched": country_unmatched,
                        "coverage_percent": "0.0",
                    }
                )

                continue

            for club in country_clubs:
                item, score, method = find_logo(
                    club["name"],
                    country_code,
                    aliases,
                    source_index,
                )

                if item is None:
                    country_unmatched += 1
                    total_unmatched += 1

                    candidate, candidate_score, _ = fuzzy_match(
                        normalize_name(club["name"]),
                        source_index,
                    )

                    unmatched_rows.append(
                        {
                            "club_id": club["id"],
                            "club": club["name"],
                            "country": club["country"],
                            "country_code": country_code,
                            "best_candidate": (
                                candidate["stem"]
                                if candidate
                                else ""
                            ),
                            "score": (
                                f"{candidate_score:.3f}"
                                if candidate
                                else ""
                            ),
                            "reason": "no_confident_match",
                        }
                    )

                    print(
                        f"[NÃO ENCONTRADO] "
                        f"{club['name']}"
                    )

                    continue

                destination = copy_logo(
                    item["path"],
                    country_code,
                    club["name"],
                )

                relative_logo = database_logo_path(
                    destination
                )

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

                country_matched += 1
                total_matched += 1

                matched_rows.append(
                    {
                        "club_id": club["id"],
                        "club": club["name"],
                        "country": club["country"],
                        "country_code": country_code,
                        "source_file": str(item["path"]),
                        "destination": relative_logo,
                        "method": method,
                        "score": f"{score:.3f}",
                    }
                )

                print(
                    f"[OK] {club['name']} "
                    f"-> {relative_logo} "
                    f"({method}, {score:.3f})"
                )

            coverage = (
                country_matched
                / len(country_clubs)
                * 100
            )

            country_summary.append(
                {
                    "country_code": country_code,
                    "country": country_clubs[0]["country"],
                    "clubs": len(country_clubs),
                    "source_images": len(source_index),
                    "matched": country_matched,
                    "unmatched": country_unmatched,
                    "coverage_percent": f"{coverage:.1f}",
                }
            )

        write_csv(
            MATCH_REPORT_FILE,
            matched_rows,
            [
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

        write_csv(
            UNMATCHED_FILE,
            unmatched_rows,
            [
                "club_id",
                "club",
                "country",
                "country_code",
                "best_candidate",
                "score",
                "reason",
            ],
        )

        write_csv(
            COUNTRY_REPORT_FILE,
            country_summary,
            [
                "country_code",
                "country",
                "clubs",
                "source_images",
                "matched",
                "unmatched",
                "coverage_percent",
            ],
        )

    print()
    print("=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)

    for row in country_summary:
        print(
            f"{row['country_code']:<4} "
            f"{row['matched']:>4}/{row['clubs']:<4} "
            f"{row['coverage_percent']:>6}%  "
            f"{row['country']}"
        )

    print("-" * 70)
    print(
        f"TOTAL: {total_matched}/"
        f"{total_matched + total_unmatched} "
        f"escudos encontrados"
    )

    print()
    print(f"Relatório completo: {MATCH_REPORT_FILE.name}")
    print(f"Não encontrados: {UNMATCHED_FILE.name}")
    print(f"Resumo por país: {COUNTRY_REPORT_FILE.name}")


if __name__ == "__main__":
    main()
