#!/usr/bin/env python3
"""
Envia os escudos já baixados em source_club_logos/ para um repositório Git separado.

Fluxo:
1. Lê source_club_logos/<PAIS>/<arquivo>.
2. Copia apenas imagens para uma pasta externa ao projeto principal.
3. Inicializa/atualiza um repositório Git nessa pasta.
4. Faz commit.
5. Faz push para o GitHub.
6. Gera um relatório JSON com os arquivos enviados.

Exemplo:
    python upload_existing_club_logos.py ^
        --remote https://github.com/SEU_USUARIO/vida-de-boleiro-logos.git

Ou usando SSH:
    python upload_existing_club_logos.py ^
        --remote git@github.com:SEU_USUARIO/vida-de-boleiro-logos.git

O script NÃO apaga source_club_logos/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = BASE_DIR / "source_club_logos"
DEFAULT_REPO_DIR = BASE_DIR.parent / "vida-de-boleiro-logos"
ALLOWED_EXTENSIONS = {".png", ".webp", ".svg", ".jpg", ".jpeg"}


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    command = ["git", *args]
    print("[GIT]", " ".join(command))
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_git_available() -> None:
    try:
        result = subprocess.run(
            ["git", "--version"],
            text=True,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise RuntimeError(
            "Git não foi encontrado. Instale/configure o Git antes de executar este script."
        )

    print("[OK]", result.stdout.strip())


def iter_logos(source_dir: Path):
    for path in sorted(source_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_logos(source_dir: Path, repo_dir: Path) -> list[dict]:
    logos_dir = repo_dir / "clubs"
    logos_dir.mkdir(parents=True, exist_ok=True)

    report = []

    logo_paths = list(iter_logos(source_dir))
    total = len(logo_paths)

    if not total:
        raise RuntimeError(f"Nenhum escudo encontrado em: {source_dir}")

    print(f"[INFO] {total} escudos encontrados.")

    for index, source_path in enumerate(logo_paths, start=1):
        relative = source_path.relative_to(source_dir)
        destination = logos_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)

        source_hash = sha256_file(source_path)

        status = "copied"
        if destination.exists():
            destination_hash = sha256_file(destination)
            if destination_hash == source_hash:
                status = "unchanged"
            else:
                shutil.copy2(source_path, destination)
                status = "updated"
        else:
            shutil.copy2(source_path, destination)

        report.append(
            {
                "source": relative.as_posix(),
                "repo_path": (Path("clubs") / relative).as_posix(),
                "sha256": source_hash,
                "status": status,
                "size_bytes": source_path.stat().st_size,
            }
        )

        if index % 50 == 0 or index == total:
            print(f"[COPIA] {index}/{total}")

    return report


def write_repo_files(repo_dir: Path, report: list[dict], owner_repo: str | None) -> None:
    readme = repo_dir / "README.md"

    readme.write_text(
        "# Vida de Boleiro — Club Logos\n\n"
        "Repositório de assets de escudos utilizados pelo projeto Vida de Boleiro.\n\n"
        "Estrutura:\n\n"
        "```text\n"
        "clubs/\n"
        "├── BRA/\n"
        "├── ARG/\n"
        "├── ENG/\n"
        "└── ...\n"
        "```\n\n"
        f"Escudos no último envio: **{len(report)}**.\n",
        encoding="utf-8",
    )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(report),
        "base_path": "clubs/",
        "github_repository": owner_repo,
        "files": report,
    }

    (repo_dir / "logos_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    gitignore = repo_dir / ".gitignore"
    gitignore.write_text(
        "__pycache__/\n"
        "*.pyc\n"
        ".DS_Store\n"
        "Thumbs.db\n",
        encoding="utf-8",
    )


def ensure_repo(repo_dir: Path, remote: str, branch: str) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)

    if not (repo_dir / ".git").exists():
        run_git(["init"], cwd=repo_dir)
        run_git(["branch", "-M", branch], cwd=repo_dir)
    else:
        print("[INFO] Repositório Git externo já existe.")

    remotes = run_git(["remote"], cwd=repo_dir).stdout.split()

    if "origin" not in remotes:
        run_git(["remote", "add", "origin", remote], cwd=repo_dir)
    else:
        current = run_git(["remote", "get-url", "origin"], cwd=repo_dir).stdout.strip()
        if current != remote:
            print(f"[INFO] Atualizando origin:\n  antigo: {current}\n  novo:   {remote}")
            run_git(["remote", "set-url", "origin", remote], cwd=repo_dir)


def commit_and_push(repo_dir: Path, branch: str, message: str) -> bool:
    run_git(["add", "."], cwd=repo_dir)

    status = run_git(["status", "--porcelain"], cwd=repo_dir).stdout.strip()

    if status:
        try:
            run_git(["commit", "-m", message], cwd=repo_dir)
        except subprocess.CalledProcessError as exc:
            print(exc.stdout)
            print(exc.stderr, file=sys.stderr)
            raise RuntimeError(
                "O commit falhou. Confira se user.name e user.email estão configurados no Git."
            ) from exc
    else:
        print("[INFO] Nenhuma alteração nova para commit.")

    try:
        result = run_git(["push", "-u", "origin", branch], cwd=repo_dir)
    except subprocess.CalledProcessError as exc:
        print(exc.stdout)
        print(exc.stderr, file=sys.stderr)
        raise RuntimeError(
            "O push falhou. Confirme se o repositório existe e se o Git está autenticado."
        ) from exc

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return True


def parse_owner_repo(remote: str) -> str | None:
    # HTTPS: https://github.com/usuario/repositorio.git
    if "github.com/" in remote:
        tail = remote.split("github.com/", 1)[1]
        return tail.removesuffix(".git").strip("/")

    # SSH: git@github.com:usuario/repositorio.git
    if "github.com:" in remote:
        tail = remote.split("github.com:", 1)[1]
        return tail.removesuffix(".git").strip("/")

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envia source_club_logos para um repositório GitHub separado."
    )
    parser.add_argument(
        "--remote",
        required=True,
        help="URL Git do repositório de escudos no GitHub.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Pasta de origem (padrão: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=DEFAULT_REPO_DIR,
        help=f"Pasta externa usada para o repositório de escudos (padrão: {DEFAULT_REPO_DIR})",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch do repositório remoto (padrão: main).",
    )
    parser.add_argument(
        "--message",
        default="Atualiza escudos dos clubes",
        help="Mensagem do commit.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Prepara e faz commit local, mas não envia ao GitHub.",
    )

    args = parser.parse_args()

    source_dir = args.source.resolve()
    repo_dir = args.repo_dir.resolve()

    if not source_dir.exists():
        raise RuntimeError(f"Pasta de origem não encontrada: {source_dir}")

    # Proteção: não criar o novo repo dentro da pasta dos escudos.
    try:
        repo_dir.relative_to(source_dir)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "--repo-dir não pode ficar dentro de source_club_logos."
        )

    ensure_git_available()
    ensure_repo(repo_dir, args.remote, args.branch)

    report = copy_logos(source_dir, repo_dir)
    owner_repo = parse_owner_repo(args.remote)
    write_repo_files(repo_dir, report, owner_repo)

    print(f"[INFO] Repositório local dos escudos: {repo_dir}")
    print(f"[INFO] Total de escudos preparados: {len(report)}")

    run_git(["add", "."], cwd=repo_dir)
    status = run_git(["status", "--short"], cwd=repo_dir).stdout
    if status:
        print("[ALTERAÇÕES]")
        lines = status.splitlines()
        preview = lines[:30]
        print("\n".join(preview))
        if len(lines) > 30:
            print(f"... e mais {len(lines) - 30} alterações.")
    else:
        print("[INFO] Nenhuma alteração detectada.")

    if args.no_push:
        print("[INFO] --no-push ativado. Nada foi enviado ao GitHub.")
        return 0

    commit_and_push(
        repo_dir,
        args.branch,
        args.message,
    )

    if owner_repo:
        raw_base = f"https://raw.githubusercontent.com/{owner_repo}/{args.branch}/clubs/"
        print()
        print("[SUCESSO] Escudos enviados.")
        print("[BASE URL]")
        print(raw_base)
        print()
        print("Exemplo:")
        print(raw_base + "BRA/santos.png")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[ERRO] {exc}", file=sys.stderr)
        raise SystemExit(1)
