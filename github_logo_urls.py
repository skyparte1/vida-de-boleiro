"""
Helper central para URLs remotas dos escudos do Vida de Boleiro.

O banco continua guardando somente o caminho relativo, por exemplo:
    BRA/flamengo.png

A URL final fica:
    https://raw.githubusercontent.com/skyparte1/vida-de-boleiro-logos/main/clubs/BRA/flamengo.png
"""

from urllib.parse import quote

GITHUB_LOGOS_OWNER = "skyparte1"
GITHUB_LOGOS_REPO = "vida-de-boleiro-logos"
GITHUB_LOGOS_BRANCH = "main"
GITHUB_LOGOS_BASE_PATH = "clubs"

RAW_BASE_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_LOGOS_OWNER}/{GITHUB_LOGOS_REPO}/"
    f"{GITHUB_LOGOS_BRANCH}/{GITHUB_LOGOS_BASE_PATH}/"
)


def club_logo_url(logo_path: str | None) -> str | None:
    """Converte o caminho relativo salvo em clubs.logo para uma URL raw do GitHub."""
    if not logo_path:
        return None

    normalized = str(logo_path).replace("\\", "/").lstrip("/")

    # Compatibilidade caso o banco já tenha "clubs/" no começo.
    prefix = f"{GITHUB_LOGOS_BASE_PATH}/"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix):]

    # Mantém as barras, mas escapa espaços/acentos caso existam.
    escaped = "/".join(quote(part) for part in normalized.split("/"))
    return RAW_BASE_URL + escaped


def remote_repo_path(logo_path: str | None) -> str | None:
    """Retorna o caminho dentro do repositório de assets."""
    if not logo_path:
        return None

    normalized = str(logo_path).replace("\\", "/").lstrip("/")
    prefix = f"{GITHUB_LOGOS_BASE_PATH}/"

    if normalized.startswith(prefix):
        return normalized

    return prefix + normalized
