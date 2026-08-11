#!/usr/bin/env python3
"""
Reconecta clubs.logo ao repositório remoto vida-de-boleiro-logos.

O script NÃO baixa escudos para static/.
Ele usa um clone local temporário/permanente do repositório de assets apenas
para indexar os arquivos e atualizar o SQLite.

Uso:
    python relink_github_logos.py

Somente um país:
    python relink_github_logos.py BRA

Refazer inclusive clubes que já possuem logo:
    python relink_github_logos.py BRA --force
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from club_logos_manager import (
    ALLOWED_EXTENSIONS,
    find_logo,
    load_aliases,
    normalize_name,
)
from database import connect

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent / "vida-de-boleiro-logos"
REMOTE = "https://github.com/skyparte1/vida-de-boleiro-logos.git"
BRANCH = "main"
CLUBS_DIR = REPO_DIR / "clubs"


def run_git(*args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=REPO_DIR if REPO_DIR.exists() else BASE_DIR.parent,
        check=True,
    )


def ensure_repo() -> None:
    if (REPO_DIR / ".git").exists():
        print("[GIT] Atualizando repositório de escudos...")
        run_git("pull", "--ff-only", "origin", BRANCH)
        return

    if REPO_DIR.exists() and any(REPO_DIR.iterdir()):
        raise RuntimeError(
            f"{REPO_DIR} existe, mas não é um repositório Git vazio."
        )

    print("[GIT] Clonando repositório de escudos...")
    subprocess.run(
        ["git", "clone", "--branch", BRANCH, REMOTE, str(REPO_DIR)],
        cwd=BASE_DIR.parent,
        check=True,
    )


def build_index(country_code: str):
    folder = CLUBS_DIR / country_code
    index = []

    if not folder.exists():
        return index

    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            normalized = normalize_name(path.stem)
            if normalized:
                index.append(
                    {
                        "path": path,
                        "stem": path.stem,
                        "normalized": normalized,
                    }
                )

    return index


def db_logo_path(path: Path) -> str:
    """
    O banco mantém o formato antigo:
        BRA/flamengo.png
    e NÃO:
        clubs/BRA/flamengo.png
    """
    return path.relative_to(CLUBS_DIR).as_posix()


def relink_country(country_code: str, force: bool = False) -> tuple[int, int, int]:
    country_code = country_code.upper()
    aliases = load_aliases()
    index = build_index(country_code)

    if not index:
        print(f"[AVISO] Nenhum escudo remoto encontrado para {country_code}.")
        return 0, 0, 0

    linked = 0
    already = 0
    unmatched = 0

    with connect() as connection:
        country = connection.execute(
            "SELECT id, name FROM countries WHERE code = ?",
            (country_code,),
        ).fetchone()

        if not country:
            raise RuntimeError(f"País não encontrado no banco: {country_code}")

        clubs = connection.execute(
            """
            SELECT id, name, logo
            FROM clubs
            WHERE country_id = ?
            ORDER BY name
            """,
            (country["id"],),
        ).fetchall()

        for club in clubs:
            if club["logo"] and not force:
                already += 1
                continue

            item, score, method = find_logo(
                club["name"],
                country_code,
                aliases,
                index,
            )

            if item is None:
                unmatched += 1
                print(f"[NÃO VINCULADO] {club['name']}")
                continue

            relative = db_logo_path(item["path"])

            connection.execute(
                "UPDATE clubs SET logo = ? WHERE id = ?",
                (relative, club["id"]),
            )

            linked += 1
            print(
                f"[LINK OK] {club['name']} -> {relative} "
                f"({method}, {score:.3f})"
            )

    return linked, already, unmatched


def get_country_codes():
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
        help="Ex.: BRA. Omitido = todos os países.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refaz também registros que já têm clubs.logo.",
    )
    args = parser.parse_args()

    ensure_repo()

    codes = (
        [args.country_code.upper()]
        if args.country_code
        else get_country_codes()
    )

    total_linked = 0
    total_already = 0
    total_unmatched = 0

    for code in codes:
        print()
        print("=" * 64)
        print(code)
        print("=" * 64)

        linked, already, unmatched = relink_country(code, args.force)
        total_linked += linked
        total_already += already
        total_unmatched += unmatched

    print()
    print(
        f"Concluído: {total_linked} novos vínculos, "
        f"{total_already} já existentes, "
        f"{total_unmatched} não vinculados."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
