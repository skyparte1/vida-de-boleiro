import argparse
import csv
import json
import re
import shutil
import unicodedata
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from database import connect

BASE_DIR = Path(__file__).parent
SOURCE_DIR = BASE_DIR / "source_club_logos"
DEST_DIR = BASE_DIR / "static" / "club_logos"
ALIASES_FILE = BASE_DIR / "club_logo_aliases.json"

MATCH_REPORT_FILE = BASE_DIR / "club_logo_match_report.csv"
UNMATCHED_FILE = BASE_DIR / "unmatched_clubs.csv"
COUNTRY_REPORT_FILE = BASE_DIR / "club_logo_country_report.csv"

ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}
FUZZY_THRESHOLD = 0.88
MIN_FUZZY_GAP = 0.04
OVERWRITE_EXISTING = False


def normalize_name(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    removable = {"fc", "cf", "ac", "afc", "sc", "club", "clube", "football", "futebol"}
    return " ".join(token for token in text.split() if token not in removable).strip()


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def ensure_logo_column():
    with connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(clubs)").fetchall()}
        if "logo" not in columns:
            connection.execute("ALTER TABLE clubs ADD COLUMN logo TEXT")
            print("[BANCO] Coluna 'logo' criada.")


def ensure_directories():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    with connect() as connection:
        countries = connection.execute("SELECT code FROM countries ORDER BY code").fetchall()

    for row in countries:
        code = row["code"]
        (SOURCE_DIR / code).mkdir(parents=True, exist_ok=True)
        (DEST_DIR / code).mkdir(parents=True, exist_ok=True)


def load_aliases():
    if not ALIASES_FILE.exists():
        ALIASES_FILE.write_text("{}\n", encoding="utf-8")
        return {}

    with ALIASES_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    aliases = {}
    for key, value in raw.items():
        if "|" in key:
            country_code, club_name = key.split("|", 1)
            aliases[(country_code.strip().upper(), normalize_name(club_name))] = normalize_name(value)
        else:
            aliases[(None, normalize_name(key))] = normalize_name(value)

    return aliases


def get_alias(aliases, country_code, club_name):
    normalized = normalize_name(club_name)
    return aliases.get((country_code, normalized)) or aliases.get((None, normalized))


def build_country_index(country_code):
    country_dir = SOURCE_DIR / country_code
    index = []

    if not country_dir.exists():
        return index

    for path in country_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            normalized = normalize_name(path.stem)
            if normalized:
                index.append({"path": path, "stem": path.stem, "normalized": normalized})
    return index


def exact_match(target, index):
    matches = [item for item in index if item["normalized"] == target]
    if len(matches) == 1:
        return matches[0], 1.0
    return None, 0.0


def fuzzy_match(target, index):
    best_item = None
    best_score = 0.0
    second_score = 0.0

    for item in index:
        score = SequenceMatcher(None, target, item["normalized"]).ratio()
        if score > best_score:
            second_score = best_score
            best_score = score
            best_item = item
        elif score > second_score:
            second_score = score

    return best_item, best_score, second_score


def find_logo(club_name, country_code, aliases, index):
    normalized = normalize_name(club_name)
    alias = get_alias(aliases, country_code, club_name)

    if alias:
        item, _ = exact_match(alias, index)
        if item:
            return item, 1.0, "alias"

        item, score, second = fuzzy_match(alias, index)
        if item and score >= FUZZY_THRESHOLD and score - second >= MIN_FUZZY_GAP:
            return item, score, "alias_fuzzy"

    item, _ = exact_match(normalized, index)
    if item:
        return item, 1.0, "exact"

    item, score, second = fuzzy_match(normalized, index)
    if item and score >= FUZZY_THRESHOLD and score - second >= MIN_FUZZY_GAP:
        return item, score, "fuzzy"

    return None, score, "unmatched"


def copy_to_final(source_path, country_code, club_name):
    country_dir = DEST_DIR / country_code
    country_dir.mkdir(parents=True, exist_ok=True)

    destination = country_dir / f"{slugify(club_name)}{source_path.suffix.lower()}"

    if not destination.exists() or OVERWRITE_EXISTING:
        shutil.copy2(source_path, destination)

    return destination


def relative_logo_path(path):
    return path.relative_to(DEST_DIR).as_posix()


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def import_all():
    ensure_logo_column()
    ensure_directories()
    aliases = load_aliases()

    with connect() as connection:
        clubs = connection.execute(
            """
            SELECT clubs.id, clubs.name, clubs.logo,
                   countries.name AS country,
                   countries.code AS country_code
            FROM clubs
            JOIN countries ON countries.id = clubs.country_id
            ORDER BY countries.code, clubs.name
            """
        ).fetchall()

        by_country = defaultdict(list)
        for club in clubs:
            by_country[club["country_code"]].append(club)

        matches = []
        unmatched = []
        country_report = []
        total_matched = 0
        total_unmatched = 0

        for country_code in sorted(by_country):
            country_clubs = by_country[country_code]
            index = build_country_index(country_code)
            matched_here = 0
            unmatched_here = 0

            print()
            print("=" * 72)
            print(f"{country_code} | {country_clubs[0]['country']} | {len(country_clubs)} clubes | {len(index)} imagens")
            print("=" * 72)

            for club in country_clubs:
                item, score, method = find_logo(club["name"], country_code, aliases, index)

                if item is None:
                    candidate, candidate_score, _ = fuzzy_match(normalize_name(club["name"]), index)

                    unmatched_here += 1
                    total_unmatched += 1
                    unmatched.append({
                        "club_id": club["id"],
                        "club": club["name"],
                        "country": club["country"],
                        "country_code": country_code,
                        "best_candidate": candidate["stem"] if candidate else "",
                        "score": f"{candidate_score:.3f}" if candidate else "",
                        "reason": "no_confident_match" if index else "country_folder_empty",
                    })
                    print(f"[NÃO ENCONTRADO] {club['name']}")
                    continue

                destination = copy_to_final(item["path"], country_code, club["name"])
                relative = relative_logo_path(destination)

                connection.execute("UPDATE clubs SET logo = ? WHERE id = ?", (relative, club["id"]))

                matched_here += 1
                total_matched += 1
                matches.append({
                    "club_id": club["id"],
                    "club": club["name"],
                    "country": club["country"],
                    "country_code": country_code,
                    "source_file": str(item["path"]),
                    "destination": relative,
                    "method": method,
                    "score": f"{score:.3f}",
                })

                print(f"[OK] {club['name']} -> {relative} ({method}, {score:.3f})")

            coverage = matched_here / len(country_clubs) * 100 if country_clubs else 0
            country_report.append({
                "country_code": country_code,
                "country": country_clubs[0]["country"],
                "clubs": len(country_clubs),
                "source_images": len(index),
                "matched": matched_here,
                "unmatched": unmatched_here,
                "coverage_percent": f"{coverage:.1f}",
            })

    write_csv(MATCH_REPORT_FILE, matches, [
        "club_id", "club", "country", "country_code",
        "source_file", "destination", "method", "score"
    ])
    write_csv(UNMATCHED_FILE, unmatched, [
        "club_id", "club", "country", "country_code",
        "best_candidate", "score", "reason"
    ])
    write_csv(COUNTRY_REPORT_FILE, country_report, [
        "country_code", "country", "clubs", "source_images",
        "matched", "unmatched", "coverage_percent"
    ])

    print()
    print("=" * 72)
    print("RESUMO FINAL")
    print("=" * 72)
    for row in country_report:
        print(f"{row['country_code']:<4} {row['matched']:>4}/{row['clubs']:<4} {row['coverage_percent']:>6}%  {row['country']}")
    print("-" * 72)
    print(f"TOTAL: {total_matched}/{total_matched + total_unmatched} encontrados")
    print()
    print(f"Matches: {MATCH_REPORT_FILE.name}")
    print(f"Problemáticos: {UNMATCHED_FILE.name}")
    print(f"Por país: {COUNTRY_REPORT_FILE.name}")


def set_manual_logo(country_code, club_name, image_path):
    ensure_logo_column()
    ensure_directories()

    country_code = country_code.upper()
    image_path = Path(image_path).expanduser().resolve()

    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extensão não suportada: {image_path.suffix}")

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT clubs.id, clubs.name
            FROM clubs
            JOIN countries ON countries.id = clubs.country_id
            WHERE clubs.name = ? AND countries.code = ?
            """,
            (club_name, country_code),
        ).fetchall()

        if not rows:
            raise RuntimeError(f"Clube não encontrado: {country_code} | {club_name}")

        if len(rows) > 1:
            raise RuntimeError(f"Mais de um clube encontrado: {country_code} | {club_name}")

        club = rows[0]
        destination_dir = DEST_DIR / country_code
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / f"{slugify(club['name'])}{image_path.suffix.lower()}"
        shutil.copy2(image_path, destination)

        relative = relative_logo_path(destination)
        connection.execute("UPDATE clubs SET logo = ? WHERE id = ?", (relative, club["id"]))

    print(f"[MANUAL OK] {country_code} | {club_name} -> {relative}")


def show_status():
    ensure_logo_column()

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT countries.code,
                   countries.name AS country,
                   COUNT(clubs.id) AS clubs,
                   SUM(CASE WHEN clubs.logo IS NOT NULL AND clubs.logo <> '' THEN 1 ELSE 0 END) AS with_logo
            FROM countries
            LEFT JOIN clubs ON clubs.country_id = countries.id
            GROUP BY countries.id
            HAVING COUNT(clubs.id) > 0
            ORDER BY countries.code
            """
        ).fetchall()

    total = 0
    with_logo = 0

    for row in rows:
        clubs = row["clubs"]
        logos = row["with_logo"] or 0
        total += clubs
        with_logo += logos
        percent = logos / clubs * 100 if clubs else 0
        print(f"{row['code']:<4} {logos:>4}/{clubs:<4} {percent:>6.1f}%  {row['country']}")

    print("-" * 60)
    percent = with_logo / total * 100 if total else 0
    print(f"TOTAL {with_logo}/{total} ({percent:.1f}%)")



def request_json(
    url,
    timeout=20,
    max_retries=5,
    retry_wait=65,
):
    """
    Faz uma requisição JSON.

    Em caso de HTTP 429 (Too Many Requests), aguarda
    e repete a mesma requisição automaticamente.
    """
    attempt = 0

    while True:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "VidaDeBoleiro/1.0"},
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
            ) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise

            attempt += 1

            if attempt > max_retries:
                raise RuntimeError(
                    "A API continuou retornando HTTP 429 "
                    f"após {max_retries} tentativas."
                ) from exc

            retry_after = exc.headers.get("Retry-After")

            try:
                wait_seconds = (
                    int(retry_after)
                    if retry_after
                    else retry_wait
                )
            except (TypeError, ValueError):
                wait_seconds = retry_wait

            wait_seconds += 2

            print()
            print(
                f"[429] Limite da API atingido. "
                f"Aguardando {wait_seconds}s para repetir "
                f"a mesma consulta..."
            )

            time.sleep(wait_seconds)


def download_binary(url, destination, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VidaDeBoleiro/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        destination.write_bytes(response.read())


def download_country(country_code, api_key="123", delay=2.2):
    """Baixa escudos do TheSportsDB para source_club_logos/<PAIS>."""
    ensure_logo_column()
    ensure_directories()

    country_code = country_code.upper()

    with connect() as connection:
        country = connection.execute(
            "SELECT id, name, code FROM countries WHERE code = ?",
            (country_code,),
        ).fetchone()

        if not country:
            raise RuntimeError(f"País não encontrado no banco: {country_code}")

        clubs = connection.execute(
            "SELECT id, name FROM clubs WHERE country_id = ? ORDER BY name",
            (country["id"],),
        ).fetchall()

    country_dir = SOURCE_DIR / country_code
    country_dir.mkdir(parents=True, exist_ok=True)

    report = []
    unmatched = []

    print(f"Baixando escudos de {country['name']} ({country_code})...")
    print(f"Clubes no banco: {len(clubs)}")
    print(
        f"Delay entre consultas: {delay:.1f}s. "
        "Se ocorrer HTTP 429, o script aguardará "
        "automaticamente e repetirá a mesma consulta."
    )

    for number, club in enumerate(clubs, 1):
        club_name = club["name"]
        print(f"[{number}/{len(clubs)}] {club_name}...", end=" ")

        existing = [
            p for p in country_dir.glob(f"{slugify(club_name)}.*")
            if p.suffix.lower() in ALLOWED_EXTENSIONS
        ]
        if existing:
            print("já existe")
            continue

        try:
            encoded = urllib.parse.quote(club_name)
            url = (
                f"https://www.thesportsdb.com/api/v1/json/"
                f"{api_key}/searchteams.php?t={encoded}"
            )
            payload = request_json(url)
            candidates = payload.get("teams") or []

            target = normalize_name(club_name)
            best = None
            best_score = 0.0

            for team in candidates:
                if (team.get("strSport") or "").lower() not in ("", "soccer"):
                    continue

                candidate_name = normalize_name(team.get("strTeam") or "")
                if not candidate_name:
                    continue

                score = SequenceMatcher(None, target, candidate_name).ratio()

                # Pequeno bônus se o país retornado for o mesmo.
                returned_country = normalize_name(team.get("strCountry") or "")
                db_country = normalize_name(country["name"])
                if returned_country and returned_country == db_country:
                    score = min(1.0, score + 0.08)

                if score > best_score:
                    best_score = score
                    best = team

            if not best or best_score < 0.82:
                print("não encontrado")
                unmatched.append({
                    "club": club_name,
                    "best_match": best.get("strTeam", "") if best else "",
                    "score": f"{best_score:.3f}" if best else "",
                    "reason": "no_confident_match",
                })
                time.sleep(delay)
                continue

            badge_url = (
                best.get("strBadge")
                or best.get("strTeamBadge")
                or best.get("strLogo")
                or ""
            )

            if not badge_url:
                print("time encontrado, mas sem escudo")
                unmatched.append({
                    "club": club_name,
                    "best_match": best.get("strTeam", ""),
                    "score": f"{best_score:.3f}",
                    "reason": "no_badge",
                })
                time.sleep(delay)
                continue

            suffix = Path(urllib.parse.urlparse(badge_url).path).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                suffix = ".png"

            destination = country_dir / f"{slugify(club_name)}{suffix}"
            download_binary(badge_url, destination)

            print(f"OK -> {destination.name}")
            report.append({
                "club": club_name,
                "matched_team": best.get("strTeam", ""),
                "score": f"{best_score:.3f}",
                "badge_url": badge_url,
                "saved_file": str(destination),
            })

        except Exception as exc:
            print(f"ERRO: {exc}")
            unmatched.append({
                "club": club_name,
                "best_match": "",
                "score": "",
                "reason": str(exc),
            })

        time.sleep(delay)

    write_csv(
        BASE_DIR / f"download_report_{country_code}.csv",
        report,
        ["club", "matched_team", "score", "badge_url", "saved_file"],
    )
    write_csv(
        BASE_DIR / f"download_unmatched_{country_code}.csv",
        unmatched,
        ["club", "best_match", "score", "reason"],
    )

    print()
    print(f"Baixados: {len(report)}")
    print(f"Não resolvidos: {len(unmatched)}")
    print("Agora executando a importação para static/club_logos e SQLite...")
    import_all()



def link_existing_logos(country_code):
    """Vincula escudos já existentes em static/club_logos/<PAIS> ao SQLite."""
    ensure_logo_column()
    ensure_directories()
    aliases = load_aliases()
    country_code = country_code.upper()
    country_dir = DEST_DIR / country_code

    with connect() as connection:
        country = connection.execute(
            "SELECT id, name FROM countries WHERE code = ?", (country_code,)
        ).fetchone()
        if not country:
            raise RuntimeError(f"País não encontrado: {country_code}")

        clubs = connection.execute(
            "SELECT id, name, logo FROM clubs WHERE country_id = ? ORDER BY name",
            (country["id"],)
        ).fetchall()

        index = []
        for path in country_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                normalized = normalize_name(path.stem)
                if normalized:
                    index.append({"path": path, "stem": path.stem, "normalized": normalized})

        linked, already = 0, 0
        unmatched = []

        for club in clubs:
            if club["logo"] and (DEST_DIR / club["logo"]).exists():
                already += 1
                continue

            item, score, method = find_logo(club["name"], country_code, aliases, index)
            if item is None:
                candidate, candidate_score, _ = fuzzy_match(normalize_name(club["name"]), index)
                unmatched.append({
                    "club_id": club["id"],
                    "club": club["name"],
                    "country_code": country_code,
                    "best_candidate": candidate["stem"] if candidate else "",
                    "score": f"{candidate_score:.3f}" if candidate else "",
                })
                print(f"[NÃO VINCULADO] {club['name']}")
                continue

            relative = relative_logo_path(item["path"])
            connection.execute(
                "UPDATE clubs SET logo = ? WHERE id = ?",
                (relative, club["id"])
            )
            linked += 1
            print(f"[LINK OK] {club['name']} -> {relative} ({method}, {score:.3f})")

    report = BASE_DIR / f"link_unmatched_{country_code}.csv"
    write_csv(report, unmatched, [
        "club_id", "club", "country_code", "best_candidate", "score"
    ])

    print()
    print(f"Novos vínculos: {linked}")
    print(f"Já vinculados: {already}")
    print(f"Não vinculados: {len(unmatched)}")
    print(f"Problemáticos: {report.name}")


def main():
    parser = argparse.ArgumentParser(description="Gerenciador de escudos do Vida de Boleiro.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("import", help="Importa automaticamente escudos por país.")
    subparsers.add_parser("status", help="Mostra cobertura de escudos no banco.")

    download = subparsers.add_parser(
        "download",
        help="Baixa escudos automaticamente do TheSportsDB e importa no banco.",
    )
    download.add_argument("country_code")
    download.add_argument("--api-key", default="123")
    download.add_argument("--delay", type=float, default=2.2)

    link = subparsers.add_parser(
        "link",
        help="Vincula escudos de static/club_logos/<PAIS> ao banco.",
    )
    link.add_argument("country_code")

    manual = subparsers.add_parser("set", help="Vincula manualmente uma imagem a um clube problemático.")
    manual.add_argument("country_code")
    manual.add_argument("club_name")
    manual.add_argument("image_path")

    args = parser.parse_args()

    if args.command in (None, "import"):
        import_all()
    elif args.command == "status":
        show_status()
    elif args.command == "download":
        download_country(args.country_code, args.api_key, args.delay)
    elif args.command == "link":
        link_existing_logos(args.country_code)

    elif args.command == "set":
        set_manual_logo(args.country_code, args.club_name, args.image_path)


if __name__ == "__main__":
    main()
