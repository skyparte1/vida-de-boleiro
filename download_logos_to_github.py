#!/usr/bin/env python3
"""
Baixa escudos DIRETAMENTE para o repositório vida-de-boleiro-logos,
atualiza clubs.logo no SQLite e faz commit/push automaticamente.

Não usa static/club_logos nem source_club_logos.

Exemplos:
    python download_logos_to_github.py BRA
    python download_logos_to_github.py ARG --delay 3
    python download_logos_to_github.py --all

Pré-requisito:
    O Git deve estar autenticado no PC para conseguir fazer push.
    Não coloque token do GitHub dentro deste arquivo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

from database import connect

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent / "vida-de-boleiro-logos"
REMOTE = "https://github.com/skyparte1/vida-de-boleiro-logos.git"
BRANCH = "main"
CLUBS_DIR = REPO_DIR / "clubs"

ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    removable = {
        "fc", "cf", "ac", "afc", "sc",
        "club", "clube", "football", "futebol"
    }
    return " ".join(
        token for token in text.split()
        if token not in removable
    ).strip()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def git(*args: str, capture: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        check=True,
        text=True,
        capture_output=capture,
    )


def ensure_repo() -> None:
    if (REPO_DIR / ".git").exists():
        print("[GIT] git pull...")
        git("pull", "--ff-only", "origin", BRANCH)
        return

    if REPO_DIR.exists() and any(REPO_DIR.iterdir()):
        raise RuntimeError(
            f"{REPO_DIR} existe, mas não é um repositório Git."
        )

    print("[GIT] Clonando vida-de-boleiro-logos...")
    subprocess.run(
        ["git", "clone", "--branch", BRANCH, REMOTE, str(REPO_DIR)],
        cwd=BASE_DIR.parent,
        check=True,
    )


def request_json(url: str, retries: int = 8):
    wait = 20

    for attempt in range(retries):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "VidaDeBoleiro/2.0"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == retries - 1:
                raise

            retry_after = exc.headers.get("Retry-After")
            seconds = int(retry_after) if retry_after and retry_after.isdigit() else wait
            print(f"[429] Aguardando {seconds}s...")
            time.sleep(seconds)
            wait = min(wait * 2, 300)

    raise RuntimeError("Número máximo de tentativas excedido.")


def download_binary(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VidaDeBoleiro/2.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        destination.write_bytes(response.read())


def find_existing(country_code: str, club_name: str) -> Path | None:
    folder = CLUBS_DIR / country_code
    slug = slugify(club_name)

    if not folder.exists():
        return None

    direct = [
        path for path in folder.glob(f"{slug}.*")
        if path.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    if direct:
        return direct[0]

    target = normalize_name(club_name)
    best = None
    best_score = 0.0

    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        score = SequenceMatcher(
            None,
            target,
            normalize_name(path.stem),
        ).ratio()

        if score > best_score:
            best_score = score
            best = path

    return best if best_score >= 0.92 else None


def search_team(club_name: str, country_name: str, api_key: str):
    encoded = urllib.parse.quote(club_name)
    url = (
        f"https://www.thesportsdb.com/api/v1/json/"
        f"{api_key}/searchteams.php?t={encoded}"
    )

    payload = request_json(url)
    candidates = payload.get("teams") or []

    target = normalize_name(club_name)
    db_country = normalize_name(country_name)

    best = None
    best_score = 0.0

    for team in candidates:
        if (team.get("strSport") or "").lower() not in ("", "soccer"):
            continue

        candidate_name = normalize_name(team.get("strTeam") or "")
        if not candidate_name:
            continue

        score = SequenceMatcher(None, target, candidate_name).ratio()

        returned_country = normalize_name(team.get("strCountry") or "")
        if returned_country and returned_country == db_country:
            score = min(1.0, score + 0.08)

        if score > best_score:
            best_score = score
            best = team

    if best is None or best_score < 0.82:
        return None, best_score

    return best, best_score


def get_badge_url(team: dict) -> str:
    return (
        team.get("strBadge")
        or team.get("strTeamBadge")
        or team.get("strLogo")
        or ""
    )


def db_path(path: Path) -> str:
    # Mantém compatibilidade com o banco atual.
    return path.relative_to(CLUBS_DIR).as_posix()


def update_database(club_id: int, path: Path) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE clubs SET logo = ? WHERE id = ?",
            (db_path(path), club_id),
        )


def download_country(
    country_code: str,
    api_key: str,
    delay: float,
) -> tuple[int, int, int]:
    country_code = country_code.upper()

    with connect() as connection:
        country = connection.execute(
            "SELECT id, name, code FROM countries WHERE code = ?",
            (country_code,),
        ).fetchone()

        if not country:
            raise RuntimeError(f"País não encontrado: {country_code}")

        clubs = connection.execute(
            """
            SELECT id, name, logo
            FROM clubs
            WHERE country_id = ?
            ORDER BY name
            """,
            (country["id"],),
        ).fetchall()

    folder = CLUBS_DIR / country_code
    folder.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    reused = 0
    unmatched = 0

    print()
    print(f"{country['name']} ({country_code}) — {len(clubs)} clubes")

    for number, club in enumerate(clubs, 1):
        print(f"[{number}/{len(clubs)}] {club['name']}...", end=" ")

        existing = find_existing(country_code, club["name"])
        if existing:
            update_database(club["id"], existing)
            reused += 1
            print(f"já existe -> {existing.name}")
            continue

        try:
            team, score = search_team(
                club["name"],
                country["name"],
                api_key,
            )

            if not team:
                unmatched += 1
                print(f"não encontrado ({score:.3f})")
                time.sleep(delay)
                continue

            badge_url = get_badge_url(team)

            if not badge_url:
                unmatched += 1
                print("sem escudo")
                time.sleep(delay)
                continue

            suffix = Path(
                urllib.parse.urlparse(badge_url).path
            ).suffix.lower()

            if suffix not in ALLOWED_EXTENSIONS:
                suffix = ".png"

            destination = folder / f"{slugify(club['name'])}{suffix}"
            download_binary(badge_url, destination)
            update_database(club["id"], destination)

            downloaded += 1
            print(
                f"OK -> {destination.name} "
                f"({team.get('strTeam', '')}, {score:.3f})"
            )

        except Exception as exc:
            unmatched += 1
            print(f"ERRO: {exc}")

        time.sleep(delay)

    return downloaded, reused, unmatched


def commit_and_push(message: str) -> None:
    git("add", "clubs")

    status = git("status", "--porcelain", capture=True).stdout.strip()

    if not status:
        print("[GIT] Nenhuma imagem nova para enviar.")
        return

    git("commit", "-m", message)
    git("push", "origin", BRANCH)
    print("[GIT] Escudos enviados para o GitHub.")


def get_all_country_codes():
    with connect() as connection:
        return [
            row["code"]
            for row in connection.execute(
                "SELECT code FROM countries ORDER BY code"
            ).fetchall()
        ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "country_code",
        nargs="?",
        help="Ex.: BRA. Use --all para todos.",
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--api-key", default="123")
    parser.add_argument("--delay", type=float, default=2.2)
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Baixa e atualiza o banco, mas não faz commit/push.",
    )
    args = parser.parse_args()

    if not args.all and not args.country_code:
        parser.error("Informe um código de país ou use --all.")

    ensure_repo()

    codes = (
        get_all_country_codes()
        if args.all
        else [args.country_code.upper()]
    )

    total_downloaded = 0
    total_reused = 0
    total_unmatched = 0

    for code in codes:
        downloaded, reused, unmatched = download_country(
            code,
            args.api_key,
            args.delay,
        )
        total_downloaded += downloaded
        total_reused += reused
        total_unmatched += unmatched

    if not args.no_push:
        commit_and_push(
            "Atualiza escudos automaticamente"
        )

    print()
    print("=" * 64)
    print(f"Novos downloads: {total_downloaded}")
    print(f"Já existentes:    {total_reused}")
    print(f"Não resolvidos:   {total_unmatched}")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
