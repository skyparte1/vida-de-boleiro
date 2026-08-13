# Competições B1

O estado de uma competição é mantido somente na carreira em sessão. O SQLite
continua sendo a fonte de clubes, países e competições permanentes.

As ligas cadastradas dos dez países são configuradas genericamente como turno e
returno, com 3/1/0 pontos e desempate por pontos, saldo e gols pró. Brasil usa
quatro quedas/acessos entre as divisões cadastradas; os demais países possuem
regras declarativas simplificadas em `COUNTRY_RULES`.

Copas nacionais possuem suporte a mata-mata em jogo único, pênaltis estatísticos
e byes. Competições continentais são, nesta B1, destinos de classificação
persistidos para a temporada seguinte; formatos e participantes próprios serão
aprofundados em uma etapa posterior.
