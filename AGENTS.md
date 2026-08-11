
# AGENTS.md — Vida de Boleiro

Este arquivo define as regras gerais para qualquer agente de código que trabalhe no projeto Vida de Boleiro.

O agente deve tratar este arquivo como orientação permanente do projeto, mas sempre priorizar instruções explícitas dadas pelo usuário na tarefa atual.

---

# 1. VISÃO GERAL DO PROJETO

## 1.1. O que é o Vida de Boleiro

Vida de Boleiro é um simulador de carreira de futebol.

O jogador cria um atleta e acompanha sua trajetória profissional desde o início da carreira até a aposentadoria.

A carreira deve representar uma trajetória esportiva plausível, com:

- desenvolvimento do jogador;
- desempenho em partidas;
- treinamentos;
- evolução de atributos;
- lesões;
- suspensões;
- fases boas e ruins;
- relacionamento com clubes;
- transferências;
- contratos;
- salário;
- valor de mercado;
- títulos;
- competições;
- convocações;
- seleção nacional;
- decisões profissionais;
- acontecimentos pessoais;
- envelhecimento;
- declínio físico;
- aposentadoria;
- histórico completo da carreira.

O objetivo principal é criar uma experiência de simulador de carreira, e não um jogo arcade.

---

# 2. PRINCÍPIOS FUNDAMENTAIS

## 2.1. Realismo

O comportamento do simulador deve buscar coerência com o futebol profissional.

Resultados e acontecimentos não devem parecer completamente aleatórios.

Devem existir relações entre:

- idade;
- overall;
- atributos;
- forma;
- condicionamento;
- moral;
- desempenho;
- qualidade do clube;
- nível da competição;
- importância da partida;
- posição;
- experiência;
- histórico;
- lesões;
- fadiga;
- contexto da temporada.

O jogador não deve ter garantia de sucesso.

Uma carreira pode:

- explodir cedo;
- evoluir lentamente;
- estagnar;
- sofrer lesões;
- mudar de clube;
- ser reserva;
- perder espaço;
- recuperar espaço;
- conquistar títulos;
- fracassar em grandes oportunidades;
- ter uma carreira excepcional;
- ter uma carreira apenas razoável.

---

## 2.2. Simulação em primeiro lugar

A lógica da carreira deve estar no sistema de simulação.

Templates, JavaScript e rotas Flask não devem conter regras complexas da carreira quando elas puderem existir em `simulation.py` ou em módulos especializados.

Frontend deve representar o estado.

Backend deve determinar o estado.

---

## 2.3. Persistência de estado

Toda informação necessária para continuar uma carreira deve estar representada no estado da carreira ou em uma estrutura persistente apropriada.

Não depender apenas de:

- variáveis JavaScript;
- estado visual do HTML;
- informações escondidas no frontend.

O backend deve ser a fonte de verdade da carreira.

---

# 3. ARQUITETURA

A arquitetura pode evoluir conforme o projeto crescer.

Não assumir que toda a lógica deve permanecer em um único arquivo.

Se um arquivo ficar excessivamente grande, o agente pode propor uma divisão modular.

Possíveis responsabilidades futuras:

```text
app.py
simulation/
    career.py
    calendar.py
    matches.py
    events.py
    training.py
    transfers.py
    contracts.py
    injuries.py
    competitions.py
    national_team.py
    progression.py
    retirement.py

data/
    countries.py
    clubs.py
    leagues.py
    competitions.py
    players.py

templates/
static/
tests/
````

Essa estrutura é uma possibilidade, não uma exigência.

Não realizar uma grande refatoração sem necessidade.

---

# 4. CAMADAS DO SISTEMA

## 4.1. Flask / aplicação

Responsável por:

* rotas;
* requisições;
* formulários;
* sessões;
* renderização;
* APIs internas;
* integração entre frontend e simulação.

Não deve conter a maior parte das regras da carreira.

---

## 4.2. Simulação

Responsável por:

* passagem do tempo;
* temporadas;
* partidas;
* eventos;
* decisões;
* treinamentos;
* evolução;
* lesões;
* transferências;
* contratos;
* competições;
* seleção;
* aposentadoria;
* resultados;
* histórico.

---

## 4.3. Dados

Dados de futebol devem ficar separados da lógica quando isso melhorar a manutenção.

Exemplos:

* países;
* clubes;
* ligas;
* competições;
* níveis de clubes;
* continentes;
* calendários;
* nomes;
* informações estáticas.

Não duplicar dados em vários arquivos.

---

## 4.4. Frontend

O frontend deve:

* exibir informações;
* permitir interação;
* enviar decisões;
* apresentar estatísticas;
* apresentar eventos;
* permitir navegação.

Não deve decidir o resultado da simulação.

---

# 5. CARREIRA

Uma carreira deve possuir, sempre que aplicável:

```text
identidade do jogador
idade
país
posição
pé dominante
clube
overall
atributos
forma
condicionamento
fadiga
moral
valor de mercado
salário
contrato
estatísticas
histórico
títulos
lesões
suspensões
convocações
histórico de clubes
histórico de temporadas
estado atual
modo de jogo
calendário
evento pendente
```

Novos sistemas podem acrescentar dados.

Não remover dados existentes sem verificar seus consumidores.

---

# 6. IDENTIDADE DO JOGADOR

O jogador deve poder possuir uma identidade consistente durante toda a carreira.

Informações como:

* nome;
* país;
* posição;
* pé dominante;

não devem mudar arbitrariamente.

Mudanças futuras devem ocorrer apenas quando fizerem sentido para a mecânica.

---

# 7. POSIÇÕES

A posição do jogador deve influenciar:

* atributos relevantes;
* avaliação;
* desempenho;
* oportunidades;
* escalação;
* estatísticas;
* valor de mercado;
* treinamentos;
* decisões.

Não tratar todas as posições da mesma forma.

A arquitetura deve permitir expansão futura de posições e funções táticas.

---

# 8. ATRIBUTOS

O sistema de atributos deve ser expansível.

A evolução deve considerar:

* idade;
* treinamento;
* desempenho;
* potencial;
* forma;
* lesões;
* contexto da carreira.

Evitar evolução linear e infinita.

O overall deve ser derivado ou atualizado de maneira consistente com os atributos.

Não criar situações em que:

```text
atributos diminuem
mas overall aumenta sem justificativa
```

ou o contrário.

---

# 9. POTENCIAL

O potencial deve ser tratado como uma característica de longo prazo, não como uma garantia.

Um jogador com potencial alto pode não atingir seu potencial.

Um jogador pode atingir níveis diferentes dependendo de:

* treinamento;
* oportunidades;
* desempenho;
* lesões;
* idade;
* contexto.

---

# 10. IDADE E DESENVOLVIMENTO

A idade deve influenciar a carreira.

De forma geral, o sistema deve permitir:

```text
início da carreira
↓
desenvolvimento
↓
auge
↓
estabilidade
↓
declínio
↓
aposentadoria
```

O comportamento exato deve ser definido pelo sistema de progressão e não por regras arbitrárias espalhadas pelo código.

---

# 11. PASSAGEM DO TEMPO

O calendário deve ser consistente.

O sistema pode trabalhar com:

* dias;
* semanas;
* meses;
* temporadas;

dependendo do modo de jogo e da necessidade da simulação.

Não assumir que uma partida sempre acontece em um intervalo fixo.

O calendário deve representar a existência de uma temporada esportiva.

---

# 12. MODOS DE SIMULAÇÃO

O projeto possui dois modos principais:

```text
realistic
accelerated
```

Não criar um terceiro modo sem solicitação explícita.

---

# 13. MODO REALISTA

O modo Realista prioriza:

* imersão;
* acontecimentos individuais;
* decisões;
* partidas detalhadas;
* ritmo natural.

Não deve existir uma regra artificial como:

```text
sempre avançar exatamente X semanas
```

O tempo deve avançar conforme o calendário e os próximos acontecimentos relevantes.

---

# 14. MODO ACELERADO

O modo Acelerado existe para percorrer uma carreira rapidamente.

Deve:

* processar temporadas rapidamente;
* ignorar jogos comuns quando apropriado;
* condensar eventos repetitivos;
* manter acontecimentos importantes;
* manter finais relevantes;
* produzir resumo da temporada.

Treinamentos repetitivos devem ser agrupados.

Exemplo:

```text
8 sessões de treinamento
```

não devem virar:

```text
Treino 1
Treino 2
Treino 3
...
Treino 8
```

Devem poder resultar em:

```text
Treinamentos da temporada
8 períodos de treinamento realizados.
```

---

# 15. PARTIDAS

Partidas são um sistema central.

Uma partida pode possuir:

* pré-jogo;
* escalação;
* condição do jogador;
* adversário;
* competição;
* placar;
* eventos;
* substituições;
* cartões;
* gols;
* assistências;
* lesões;
* desempenho;
* avaliação;
* resultado.

---

# 16. PARTIDAS NO REALISTA

No Realista, partidas relevantes podem ser acompanhadas através de eventos.

Exemplo:

```text
pré-jogo
↓
primeiro tempo
↓
evento
↓
intervalo
↓
segundo tempo
↓
evento
↓
final
```

O usuário deve conseguir interagir com os eventos relevantes.

Após o último evento da partida:

* a partida deve ser encerrada;
* as estatísticas devem ser atualizadas;
* o evento pendente deve ser limpo;
* o próximo estado deve ser preparado.

Nunca deixar o usuário preso no final de uma partida.

---

# 17. PARTIDAS NO ACELERADO

Jogos comuns podem ser simulados silenciosamente.

Finais e partidas de grande importância podem permanecer visíveis.

A importância de uma partida deve ser determinada pelo contexto da competição e não apenas por uma condição arbitrária.

---

# 18. COMPETIÇÕES

A arquitetura deve permitir diferentes competições.

Exemplos futuros:

* campeonato nacional;
* copa nacional;
* competições continentais;
* torneios internacionais;
* competições de seleção;
* torneios de base, quando aplicável.

Cada competição pode possuir:

* formato;
* calendário;
* número de partidas;
* fases;
* classificação;
* mata-mata;
* final;
* campeão.

Não assumir que toda competição funciona como um campeonato de pontos corridos.

---

# 19. FINAIS

Finais devem possuir importância maior.

Podem gerar:

* maior atenção;
* maior impacto na reputação;
* maior peso histórico;
* títulos;
* eventos especiais;
* avaliação diferenciada.

No modo Acelerado, finais são acontecimentos prioritários.

---

# 20. TREINAMENTOS

Treinamentos devem influenciar a carreira.

Podem afetar:

* atributos;
* forma;
* condicionamento;
* fadiga;
* moral;
* desenvolvimento.

Treinamento não deve ser apenas uma tela sem impacto real.

No modo Acelerado, múltiplos treinamentos devem ser condensados.

---

# 21. FADIGA E CONDICIONAMENTO

Fadiga deve possuir relação com:

* partidas;
* treinamentos;
* descanso;
* calendário;
* sequência de jogos.

Não permitir crescimento indefinido da fadiga sem consequências.

Condicionamento deve ser diferente de forma quando o sistema precisar representar os dois conceitos.

---

# 22. FORMA

Forma deve representar o momento atual do jogador.

Pode ser influenciada por:

* desempenho recente;
* sequência de jogos;
* treinamento;
* descanso;
* moral;
* lesões.

Forma não deve ser confundida com overall.

---

# 23. MORAL

Moral pode ser influenciada por:

* minutos;
* titularidade;
* resultados;
* títulos;
* transferências;
* relacionamento com clube;
* convocações;
* decisões da carreira.

Moral deve ter impacto moderado e coerente.

---

# 24. LESÕES

O sistema deve permitir lesões de diferentes gravidades.

Exemplos conceituais:

```text
leve
moderada
grave
muito grave
```

Lesões podem afetar:

* disponibilidade;
* atributos;
* forma;
* condicionamento;
* valor de mercado;
* carreira;
* recuperação.

Não criar lesões constantes apenas para aumentar dificuldade.

---

# 25. SUSPENSÕES E CARTÕES

O sistema deve poder representar:

* cartões amarelos;
* cartões vermelhos;
* suspensão;
* acúmulo de cartões.

A suspensão deve afetar a disponibilidade do jogador nas partidas apropriadas.

---

# 26. ESCALAÇÃO E MINUTOS

O jogador não deve necessariamente ser titular em todas as partidas.

A utilização deve considerar:

* overall;
* posição;
* concorrência;
* forma;
* moral;
* condicionamento;
* confiança do treinador;
* importância da partida;
* contexto do clube.

Isso permite:

```text
titular
reserva
não relacionado
entrada no segundo tempo
substituído
```

---

# 27. DESEMPENHO

O desempenho em uma partida deve ser probabilístico, mas influenciado por fatores reais.

Evitar:

```text
random.randint(...)
```

como único determinante de tudo.

O resultado deve considerar contexto.

---

# 28. ESTATÍSTICAS

O sistema deve preservar estatísticas de:

* partidas;
* gols;
* assistências;
* títulos;
* minutos, quando implementado;
* cartões;
* outras estatísticas relevantes.

Devem existir:

```text
estatísticas da temporada
estatísticas da carreira
```

quando aplicável.

Não misturar estatísticas de temporadas sem controle.

---

# 29. TRANSFERÊNCIAS

Transferências devem considerar:

* desempenho;
* overall;
* idade;
* potencial;
* posição;
* valor de mercado;
* reputação;
* clube atual;
* nível dos clubes;
* situação contratual;
* oportunidades.

O jogador não deve poder receber propostas absurdas constantemente.

---

# 30. MERCADO E VALOR

Valor de mercado deve evoluir de forma dinâmica.

Pode considerar:

* idade;
* overall;
* potencial;
* desempenho;
* clube;
* competição;
* títulos;
* contrato;
* lesões.

O valor não deve simplesmente aumentar a cada temporada.

---

# 31. CONTRATOS

O sistema deve poder futuramente representar:

* duração;
* salário;
* renovação;
* término;
* negociação;
* interesse de outros clubes.

Não permitir transferências incompatíveis com o estado contratual sem uma regra que justifique.

---

# 32. SALÁRIO

Salário deve possuir relação com:

* nível do clube;
* overall;
* reputação;
* desempenho;
* idade;
* mercado;
* contrato.

Não utilizar salário apenas como número decorativo se o sistema financeiro for implementado.

---

# 33. SELEÇÃO NACIONAL

A seleção deve ser um sistema separado da carreira de clubes.

Pode envolver:

* convocação;
* amistosos;
* eliminatórias;
* competições;
* Copa do Mundo;
* títulos;
* estatísticas internacionais.

A convocação deve depender de desempenho e contexto.

---

# 34. CONVOCAÇÕES

O jogador não deve ser automaticamente convocado apenas por ter overall alto.

Considerar:

* posição;
* concorrência;
* forma;
* desempenho;
* reputação;
* idade;
* importância do jogador;
* contexto da seleção.

---

# 35. EVENTOS NARRATIVOS

Eventos devem tornar a carreira mais interessante.

Podem envolver:

* decisões profissionais;
* imprensa;
* treinador;
* clube;
* torcida;
* seleção;
* família;
* contratos;
* transferências;
* recuperação;
* crises;
* conquistas.

Eventos não devem aparecer em quantidade exagerada.

---

# 36. SISTEMA DE DECISÕES

Decisões devem possuir consequências.

Evitar opções em que:

```text
Opção A
Opção B
Opção C
```

todas produzem exatamente o mesmo resultado.

As consequências podem ser:

* imediatas;
* temporárias;
* de longo prazo.

Nem toda consequência precisa ser explicitamente revelada ao jogador.

---

# 37. EVENTOS PENDENTES

O estado deve garantir que exista no máximo um evento interativo principal pendente por vez.

Exemplo:

```text
pending_event
```

não deve ser sobrescrito antes da resolução.

Filas podem ser utilizadas para acontecimentos futuros.

---

# 38. HISTÓRICO

O histórico da carreira deve registrar acontecimentos relevantes.

Exemplos:

* estreia;
* gol marcante;
* transferência;
* título;
* convocação;
* lesão importante;
* recorde;
* aposentadoria.

Não registrar dezenas de acontecimentos irrelevantes apenas para aumentar o tamanho do histórico.

---

# 39. TÍTULOS

Títulos devem ser registrados de forma estruturada.

Quando possível, guardar:

* competição;
* temporada;
* clube;
* contexto.

Não contar títulos apenas pelo tamanho de uma lista se a estrutura puder ficar inconsistente.

---

# 40. APOSENTADORIA

A carreira deve possuir encerramento.

A aposentadoria pode acontecer por:

* decisão do jogador;
* idade;
* declínio;
* contexto;
* eventos.

Ao finalizar:

```text
status = finished
```

deve ser definido de maneira consistente.

---

# 41. CARD FINAL

O card final é uma representação da carreira encerrada.

Deve conter informações relevantes como:

* nome;
* país;
* posição;
* clubes;
* overall;
* estatísticas;
* títulos;
* destaques.

O usuário deve poder baixar o card.

O card não deve depender de um serviço externo para funcionar.

---

# 42. PAÍSES

O sistema deve permitir seleção de países.

Os países devem possuir:

* código;
* nome;
* bandeira.

Os nomes exibidos ao usuário devem estar em português quando esse for o idioma da interface.

---

# 43. BANDEIRAS

O sistema de bandeiras deve ser preservado.

Não substituir por emojis.

A estrutura atual utiliza arquivos SVG e classes CSS.

Ao alterar a seleção de países:

* verificar caminhos;
* verificar classes;
* verificar arquivos;
* verificar `base.html`;
* verificar CSS.

Nunca remover bandeiras existentes para resolver outro problema.

---

# 44. CLUBES

Clubes devem ser tratados como entidades estruturadas.

Sempre que possível, possuir:

* nome;
* país;
* liga;
* nível;
* reputação;
* força;
* competição;
* histórico.

Evitar espalhar nomes de clubes como strings aleatórias por vários arquivos.

---

# 45. DADOS REALISTAS

Dados reais podem ser usados quando fizerem parte do escopo do projeto.

Quando dados externos forem adicionados:

* manter estrutura consistente;
* evitar duplicação;
* documentar origem quando necessário;
* não depender de APIs externas sem necessidade.

---

# 46. LOCALIZAÇÃO

A interface principal deve permanecer em português.

Termos técnicos internos podem permanecer em inglês quando isso fizer sentido para o código.

Exemplo:

```text
accelerated
realistic
pending_event
```

podem permanecer internos.

Na interface:

```text
Modo Acelerado
Modo Realista
Acontecimento
Temporada
```

---

# 47. RESPONSIVIDADE

O site deve funcionar em:

* desktop;
* notebook;
* tablet;
* celular.

Não criar layouts que funcionem apenas em uma resolução.

---

# 48. CSS

Preferir alterações localizadas.

Não alterar estilos globais sem necessidade.

Não reformatar arquivos inteiros apenas para uma pequena alteração.

Não apagar estilos existentes sem verificar onde são usados.

---

# 49. JAVASCRIPT

JavaScript deve ser utilizado quando necessário para:

* interações;
* componentes;
* filtros;
* navegação;
* feedback visual.

A lógica crítica da carreira deve permanecer no backend.

Não confiar em JavaScript para impedir manipulação de estado.

---

# 50. TEMPLATES

Antes de modificar um template:

* verificar `extends`;
* verificar blocks;
* verificar scripts;
* verificar classes;
* verificar variáveis fornecidas pelo Flask.

Não adicionar `<head>` duplicado em templates que herdam de `base.html`.

---

# 51. APIs

APIs internas devem possuir:

* entrada validada;
* resposta consistente;
* tratamento de erros.

Não confiar em dados enviados pelo frontend.

---

# 52. VALIDAÇÃO

Toda entrada do usuário deve ser validada no servidor.

Isso inclui:

* país;
* clube;
* posição;
* modo;
* decisões;
* valores;
* parâmetros.

Não considerar validação JavaScript suficiente.

---

# 53. SESSÃO

A sessão deve armazenar apenas o necessário.

Não colocar objetos gigantes ou dados desnecessários na sessão se puderem ficar no armazenamento apropriado.

---

# 54. ERROS

Quando ocorrer um erro:

1. reproduzir;
2. localizar a causa;
3. corrigir;
4. testar novamente.

Não mascarar exceções indiscriminadamente.

Evitar:

```python
except:
    pass
```

sem justificativa.

---

# 55. DEPENDÊNCIAS

Não adicionar bibliotecas sem necessidade.

Antes de adicionar uma dependência:

* verificar se a funcionalidade já pode ser feita com o que existe;
* verificar manutenção;
* verificar compatibilidade;
* verificar impacto no projeto.

---

# 56. TESTES

O projeto deve evoluir para possuir testes automatizados.

Priorizar testes para:

* criação de carreira;
* avanço de calendário;
* evolução;
* partidas;
* decisões;
* transferências;
* lesões;
* temporadas;
* modos Realista e Acelerado;
* aposentadoria;
* card final.

---

# 57. TESTES DE REGRESSÃO

Toda alteração relevante deve verificar se não quebrou:

* criação de carreira;
* seleção de país;
* bandeiras;
* seleção de clube;
* modos de jogo;
* partidas;
* eventos;
* treinamentos;
* transferências;
* card final.

---

# 58. DEBUG

Durante desenvolvimento, logs podem ser utilizados.

Logs devem ajudar a identificar:

* estado da carreira;
* avanço do calendário;
* evento atual;
* decisões;
* transição de temporadas;
* resultados de partidas.

Não deixar logs excessivamente verbosos na versão final sem necessidade.

---

# 59. PERFORMANCE

O simulador deve conseguir processar temporadas aceleradas sem travar desnecessariamente.

Evitar loops infinitos.

Todo processamento de simulação deve possuir condições claras de encerramento.

Quando houver filas de eventos:

* evitar duplicações;
* evitar processamento infinito;
* evitar filas gigantes de eventos irrelevantes.

---

# 60. RANDOMIZAÇÃO

Aleatoriedade deve existir, mas ser controlada.

Sempre que possível:

```text
resultado = contexto + atributos + estado + aleatoriedade
```

e não apenas:

```text
resultado = aleatoriedade
```

---

# 61. CONSISTÊNCIA DO ESTADO

Depois de cada ação importante, o estado da carreira deve permanecer válido.

Exemplo:

Se o jogador for transferido:

* clube deve mudar;
* histórico deve ser atualizado;
* valor deve continuar válido;
* contrato deve ser atualizado;
* evento deve ser encerrado;
* temporada deve continuar consistente.

Não atualizar apenas a informação visual.

---

# 62. ATOMICIDADE DAS DECISÕES

Uma decisão deve ser aplicada uma única vez.

Evitar que:

```text
duplo clique
refresh
reenvio do formulário
```

aplique a mesma decisão duas vezes.

---

# 63. REFRESH

Atualizar a página não deve:

* duplicar eventos;
* duplicar partidas;
* aplicar decisões novamente;
* avançar a carreira involuntariamente.

---

# 64. VERSÕES

O projeto evolui por versões:

```text
0.1
0.2
0.2.1
0.2.2
0.3
...
```

Uma nova versão pode adicionar sistemas maiores.

Não implementar funcionalidades planejadas para versões futuras sem autorização.

Se o usuário disser:

> "Isso fica para a 0.3"

não implementar na versão atual.

---

# 65. COMPATIBILIDADE ENTRE VERSÕES

Alterações novas devem preservar funcionalidades existentes sempre que possível.

Se uma alteração exigir mudança incompatível:

1. identificar;
2. explicar;
3. atualizar os consumidores;
4. testar.

Nunca deixar funções quebradas simplesmente porque uma nova versão mudou sua assinatura.

---

# 66. REFACTORING

Refatoração é permitida quando realmente melhora:

* manutenção;
* legibilidade;
* segurança;
* performance;
* testabilidade.

Não refatorar apenas por preferência pessoal.

Não combinar uma grande refatoração com uma funcionalidade não relacionada sem necessidade.

---

# 67. REGRA DE OURO PARA ALTERAÇÕES

Antes de alterar:

```text
ENTENDER
↓
LOCALIZAR
↓
ALTERAR
↓
TESTAR
↓
VERIFICAR REGRESSÕES
```

Nunca:

```text
ALTERAR
↓
torcer para funcionar
```

---

# 68. NÃO QUEBRAR FUNCIONALIDADES EXISTENTES

Especial atenção para:

* bandeiras;
* seleção de países;
* seleção de clubes;
* criação da carreira;
* modos;
* partidas;
* eventos;
* treinamentos;
* transferências;
* card final;
* download do card.

Se uma funcionalidade já está funcionando, não alterá-la sem motivo.

---

# 69. ALTERAÇÕES MÍNIMAS

Para bugs localizados:

Preferir:

```text
pequena alteração
```

em vez de:

```text
reescrever arquivo inteiro
```

Só reescrever uma parte grande quando houver justificativa técnica.

---

# 70. ARQUIVOS DO USUÁRIO

Nunca apagar ou sobrescrever alterações feitas pelo usuário sem autorização.

Antes de mudanças grandes:

* verificar `git status`;
* verificar diff;
* preservar trabalho não relacionado.

---

# 71. GIT

O agente deve:

* verificar o estado do repositório;
* evitar operações destrutivas;
* não usar `git reset --hard` sem autorização;
* não apagar branches;
* não sobrescrever alterações não commitadas;
* não criar commits automaticamente, salvo solicitação.

Quando solicitado a preparar uma alteração para commit:

* garantir que apenas os arquivos relacionados sejam incluídos.

---

# 72. DOCUMENTAÇÃO

Novos sistemas complexos devem possuir documentação mínima.

Documentar:

* propósito;
* entradas;
* saídas;
* regras importantes;
* dependências.

Não documentar cada linha de código.

---

# 73. AGENTE DEVE ANALISAR O PROJETO

Antes de implementar uma solicitação significativa, o agente deve primeiro descobrir:

* estrutura de arquivos;
* ponto de entrada;
* fluxo da carreira;
* fluxo de eventos;
* estado da sessão;
* templates envolvidos;
* JavaScript relacionado;
* CSS relacionado;
* testes existentes.

Não assumir a arquitetura apenas pelo nome dos arquivos.

---

# 74. IMPLEMENTAÇÃO DE NOVOS SISTEMAS

Para uma nova mecânica:

## Etapa 1 — Estado

Definir quais dados precisam existir.

## Etapa 2 — Simulação

Definir como a mecânica funciona internamente.

## Etapa 3 — Integração

Integrar com calendário, carreira e eventos.

## Etapa 4 — Interface

Mostrar a mecânica ao usuário.

## Etapa 5 — Testes

Testar casos normais e extremos.

---

# 75. CASOS EXTREMOS

Considerar situações como:

* carreira muito curta;
* jogador muito jovem;
* jogador muito velho;
* aposentadoria;
* lesão longa;
* clube sem partidas;
* temporada sem título;
* temporada excepcional;
* múltiplos eventos;
* eventos consecutivos;
* fila vazia;
* fila cheia;
* decisão inválida;
* refresh;
* formulário inválido;
* clube inválido;
* país inválido;
* final de temporada;
* final de competição.

---

# 76. FUTURAS EXPANSÕES

A arquitetura deve permitir futuramente, quando solicitado:

* sistema financeiro;
* contratos;
* salários;
* agentes;
* reputação;
* imprensa;
* torcida;
* relacionamento com treinador;
* relacionamento com companheiros;
* rivalidades;
* seleção nacional;
* competições internacionais;
* prêmios individuais;
* recordes;
* estatísticas avançadas;
* histórico completo de clubes;
* banco de reservas;
* escalações;
* tática;
* diferentes estilos de jogador;
* objetivos de carreira;
* eventos narrativos;
* sistema de conquistas;
* rankings;
* comparação entre jogadores;
* temporadas históricas;
* aposentadoria detalhada.

Não implementar esses sistemas automaticamente apenas porque estão documentados aqui.

Este arquivo define possibilidades arquiteturais, não um backlog obrigatório.

---

# 77. O QUE NÃO FAZER

Nunca:

* quebrar uma funcionalidade existente para implementar outra;
* apagar código sem entender sua função;
* substituir arquivos inteiros sem necessidade;
* criar dependências desnecessárias;
* confiar no frontend para regras importantes;
* usar aleatoriedade como único fator de simulação;
* criar eventos repetitivos excessivos;
* criar loops de simulação sem limite;
* ignorar erros;
* esconder exceções;
* alterar dados reais sem verificar consequências;
* remover bandeiras;
* trocar bandeiras por emojis;
* criar novos modos sem autorização;
* implementar funcionalidades futuras sem autorização;
* fazer refatorações gigantes durante correções pequenas;
* fazer commits sem solicitação.

---

# 78. PRIORIDADE DAS INSTRUÇÕES

Quando houver conflito:

1. instrução explícita do usuário na tarefa atual;
2. requisitos funcionais do projeto;
3. este AGENTS.md;
4. boas práticas de engenharia;
5. preferências pessoais do agente.

Se uma solicitação do usuário contradizer uma regra deste arquivo, a solicitação explícita do usuário vence, desde que seja tecnicamente possível e segura.

---

# 79. CONCLUSÃO DE UMA TAREFA

Ao terminar uma tarefa, informar:

### Alterações

Quais arquivos foram modificados e por quê.

### Funcionalidade

O que foi implementado ou corrigido.

### Testes

Quais fluxos foram testados.

### Problemas

Quais problemas permanecem, se houver.

Não afirmar que algo foi testado se não foi realmente testado.

---

# 80. PRINCÍPIO FINAL

O Vida de Boleiro deve crescer como um simulador coerente.

Cada nova funcionalidade deve contribuir para:

* realismo;
* profundidade;
* variedade;
* consistência;
* imersão;
* facilidade de manutenção.

O objetivo não é apenas adicionar funcionalidades.

O objetivo é construir um sistema de carreira de futebol em que as funcionalidades existentes continuem funcionando juntas conforme o projeto cresce.

```

