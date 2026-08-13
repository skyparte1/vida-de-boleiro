"""Fachada de compatibilidade para o motor de eventos.

As regras vivem em :mod:`career_engine`; este arquivo preserva os imports das
rotas e de integrações que usavam o módulo antigo.
"""

from career_engine import (  # noqa: F401
    advance_career,
    advance_week,
    club_stats,
    create_career,
    available_player_actions,
    ensure_career_state,
    final_card_svg,
    market_value,
    resolve_decision,
    perform_player_action,
    retire,
    update_market_value,
)
