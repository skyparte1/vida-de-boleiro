# Vida de Boleiro — orientações

- Preserve a separação entre interface (`templates/`, `static/`), persistência (`database.py`), catálogo do mundo (`football_data.py`) e regras de carreira (`simulation.py`).
- Não coloque regras de simulação nas rotas Flask.
- Dados de clubes, ligas e países devem continuar declarativos para facilitar expansão e revisão.
- Toda nova mecânica deve ter consequências persistidas no perfil do jogador.
