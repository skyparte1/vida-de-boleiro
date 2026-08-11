#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_LOGOS_DIR = PROJECT_ROOT / "static" / "club_logos"

LOGOS_REPO_DIR = PROJECT_ROOT.parent / "vida-de-boleiro-logos"
REMOTE = "https://github.com/skyparte1/vida-de-boleiro-logos.git"
BRANCH = "main"
REMOTE_CLUBS_DIR = LOGOS_REPO_DIR / "clubs"

ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}


def git(*args: str, capture: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=LOGOS_REPO_DIR,
        check=True,
        text=True,
        capture_output=capture,
    )


def ensure_repo() -> None:
    if (LOGOS_REPO_DIR / ".git").exists():
        print("[GIT] Atualizando repositório de escudos...")
        git("pull", "--ff-only", "origin", BRANCH)
        return

    if LOGOS_REPO_DIR.exists() and any(LOGOS_REPO_DIR.iterdir()):
        raise RuntimeError(
            f"{LOGOS_REPO_DIR} existe, mas não é um repositório Git."
        )

    print("[GIT] Clonando repositório de escudos...")
    subprocess.run(
        ["git", "clone", "--branch", BRANCH, REMOTE, str(LOGOS_REPO_DIR)],
        cwd=PROJECT_ROOT.parent,
        check=True,
    )


def iter_local_logos():
    if not LOCAL_LOGOS_DIR.exists():
        raise RuntimeError(
            f"Pasta local de escudos não encontrada: {LOCAL_LOGOS_DIR}"
        )

    for path in LOCAL_LOGOS_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            yield path


def same_file(source: Path, destination: Path) -> bool:
    try:
        return (
            source.stat().st_size == destination.stat().st_size
            and source.read_bytes() == destination.read_bytes()
        )
    except OSError:
        return False


def migrate(dry_run: bool = False):
    copied = 0
    skipped_existing = 0
    identical_existing = 0
    conflicts = 0

    local_files = list(iter_local_logos())

    print()
    print(f"Escudos locais encontrados: {len(local_files)}")
    print()

    for source in local_files:
        relative = source.relative_to(LOCAL_LOGOS_DIR)
        destination = REMOTE_CLUBS_DIR / relative

        if destination.exists():
            skipped_existing += 1

            if same_file(source, destination):
                identical_existing += 1
                print(f"[IGUAL] {relative.as_posix()}")
            else:
                conflicts += 1
                print(
                    f"[CONFLITO] {relative.as_posix()} "
                    "(já existe no repositório com conteúdo diferente)"
                )
            continue

        print(f"[COPIAR] {relative.as_posix()}")

        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        copied += 1

    return {
        "total_local": len(local_files),
        "copied": copied,
        "skipped_existing": skipped_existing,
        "identical_existing": identical_existing,
        "conflicts": conflicts,
    }


def commit_and_push() -> None:
    git("add", "clubs")
    status = git("status", "--porcelain", capture=True).stdout.strip()

    if not status:
        print()
        print("[GIT] Nenhum arquivo novo para enviar.")
        return

    print()
    print("[GIT] Criando commit...")
    git("commit", "-m", "Migra escudos locais restantes")

    print("[GIT] Enviando para o GitHub...")
    git("push", "origin", BRANCH)

    print("[GIT] Push concluído.")


def count_remote_logos() -> int:
    if not REMOTE_CLUBS_DIR.exists():
        return 0

    return sum(
        1
        for path in REMOTE_CLUBS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria copiado sem alterar arquivos.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Copia os arquivos, mas não faz git commit/push.",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("VIDA DE BOLEIRO - MIGRAÇÃO DE ESCUDOS LOCAIS")
    print("=" * 72)

    ensure_repo()

    before = count_remote_logos()
    stats = migrate(dry_run=args.dry_run)

    after = before + stats["copied"] if args.dry_run else count_remote_logos()

    print()
    print("=" * 72)
    print("RESUMO")
    print("=" * 72)
    print(f"Escudos locais:                {stats['total_local']}")
    print(f"Já existentes no repositório: {stats['skipped_existing']}")
    print(f" - idênticos:                  {stats['identical_existing']}")
    print(f" - conflitos:                  {stats['conflicts']}")
    print(f"Novos a copiar:                {stats['copied']}")
    print(f"Escudos no repo antes:         {before}")
    print(f"Escudos no repo depois:        {after}")

    if stats["conflicts"]:
        print()
        print("ATENÇÃO: conflitos não foram sobrescritos.")

    if args.dry_run:
        print()
        print("DRY-RUN concluído. Nenhum arquivo foi alterado.")
        return 0

    if not args.no_push:
        commit_and_push()
    else:
        print()
        print("Arquivos copiados, mas nenhum commit/push foi executado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
