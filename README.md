# Vida de Boleiro

Simulador de carreira de futebol por sessão. O usuário cria um atleta de qualquer uma das 211 associações-membro da FIFA, inicia aos 16 anos, avança semana a semana, toma decisões e recebe um card final baixável. A carreira existe apenas na memória temporária do servidor e nunca é salva em banco de dados.

## Executar

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000` no navegador.

## Regra de clube inicial

O jogador escolhe sua associação. Se houver liga disponível, recebe três clubes daquela liga; sem ela, o jogo usa uma liga disponível da mesma confederação, definida em `football_data.py`. Clubes pequenos têm 85% de peso, médios 14% e grandes 1%.
