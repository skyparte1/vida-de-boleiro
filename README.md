# Vida de Boleiro

Simulador web de carreira de futebol. A primeira versão permite criar um atleta, sugerir um clube inicial conforme país/liga, acompanhar a perna fraca e avançar temporadas.

## Executar

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000` no navegador.

## Regra de clube inicial

O jogador escolhe seu país. Se houver liga disponível, recebe três clubes daquela liga; sem ela, o jogo usa a liga disponível mais próxima definida em `football_data.py`. Clubes pequenos têm 85% de peso, médios 14% e grandes 1%.
