# Dossie de Apresentacao

## Estudo de Threads

Simulador visual de concorrencia em cruzamento sem sincronismo

### Identificacao

- Projeto: Estudo de Threads
- Tema central: concorrencia, threads, regiao critica e race condition
- Stack principal: FastAPI, Python, HTML, CSS, JavaScript e WebSocket
- Formato do sistema: backend local + frontend estatico
- Finalidade: demonstrar, de forma visual, o efeito da execucao concorrente sem sincronismo

### Sugestao para a capa na apresentacao oral

- Nome da disciplina
- Nome do professor
- Nome dos 3 integrantes
- Instituicao
- Data da apresentacao

## 1. Visao Geral do Projeto

O projeto "Estudo de Threads" foi desenvolvido para transformar um conceito teorico de sistemas concorrentes em uma demonstracao visual e interativa. Em vez de explicar threads apenas com definicoes abstratas, o sistema mostra carros atravessando um cruzamento, cada um controlado por sua propria thread no backend.

O ponto central do projeto e a ausencia de sincronismo na area critica do cruzamento. Isso permite que duas ou mais threads acessem ao mesmo tempo uma regiao compartilhada do sistema, o que representa uma race condition. Como resultado, o usuario consegue observar colisoes, estados intermediarios e variacoes entre uma execucao e outra.

Em termos didaticos, o projeto funciona muito bem porque aproxima o conteudo tecnico de algo visualmente intuitivo. Em vez de apenas dizer que "threads podem competir por um recurso compartilhado", o sistema mostra essa disputa acontecendo em tempo real.

## 2. Problema que o Projeto Demonstra

Em programacao concorrente, diversos fluxos de execucao podem tentar acessar dados compartilhados simultaneamente. Quando isso ocorre sem coordenacao adequada, surgem problemas classicos como:

- race condition
- comportamento nao deterministico
- inconsistencias de estado
- conflitos em regiao critica
- dificuldade de reproducao de erros

O projeto reproduz esse problema por meio de um cruzamento. O cruzamento representa um recurso compartilhado. Os carros representam threads independentes. Quando essas threads entram no mesmo espaco de conflito sem controle de acesso, pode acontecer colisao.

## 3. Objetivo Geral

Apresentar, de forma pratica, visual e interativa, como threads se comportam em um ambiente concorrente sem sincronismo, destacando a importancia da coordenacao de acesso a recursos compartilhados.

## 4. Objetivos Especificos

- representar cada carro como uma thread independente
- simular entradas concorrentes em uma regiao critica
- mostrar visualmente estados de execucao das threads
- registrar eventos relevantes durante a simulacao
- permitir ajuste de parametros como quantidade de carros, velocidade e dispersao de partida
- demonstrar que resultados diferentes podem ocorrer em execucoes diferentes
- servir como base para comparacoes futuras com uma versao sincronizada

## 5. Arquitetura do Sistema

O projeto esta dividido em duas partes principais:

### 5.1 Backend

O backend foi construido em Python com FastAPI. Ele concentra a logica da simulacao e faz o gerenciamento do estado global do sistema.

Responsabilidades do backend:

- criar e controlar as threads dos carros
- manter o estado atual de cada carro
- calcular a entrada e saida da regiao critica
- detectar colisoes
- atualizar estatisticas
- expor endpoints HTTP para iniciar, resetar e ajustar a simulacao
- transmitir o estado em tempo real via WebSocket

### 5.2 Frontend

O frontend e uma interface estatica em HTML, CSS e JavaScript. Ele nao executa a simulacao em si, mas consome os dados enviados pelo backend e transforma essas informacoes em uma visualizacao compreensivel.

Responsabilidades do frontend:

- desenhar o cruzamento no canvas
- renderizar os carros em movimento
- exibir estatisticas da simulacao
- mostrar o estado de cada thread
- exibir o log de eventos em tempo real
- enviar comandos de inicio, reset e ajuste de velocidade

## 6. Estrutura de Pastas

```text
Estudo-de-Threads/
|-- backend/
|   |-- main.py
|   |-- requirements.txt
|   |-- models/
|   |-- routes/
|   `-- services/
|-- frontend/
|   |-- index.html
|   |-- script.js
|   `-- style.css
|-- docs/
|   |-- dossie-apresentacao-estudo-de-threads.md
|   `-- dossie-apresentacao-estudo-de-threads.pdf
`-- README.md
```

## 7. Como a Simulacao Funciona

### 7.1 Modelo conceitual

O sistema representa um cruzamento com quatro sentidos principais:

- norte
- sul
- leste
- oeste

Cada carro nasce em uma pista fixa, recebe uma velocidade individual e percorre uma rota predefinida atraves do cruzamento.

### 7.2 Um carro por thread

Cada carro e executado em uma thread separada. Isso significa que o backend cria varios fluxos de execucao rodando em paralelo, simulando concorrencia real.

Essa decisao e importante porque o objetivo do projeto nao e apenas animar carros na tela. O objetivo e associar cada carro a uma unidade real de execucao concorrente.

### 7.3 Regiao critica

O centro do cruzamento funciona como regiao critica. Essa area foi dividida em quatro quadrantes para que a deteccao de conflitos fique mais precisa.

Os quadrantes permitem identificar em qual parte da area compartilhada cada carro esta. Assim, o sistema consegue dizer se duas direcoes realmente entram em conflito naquela sub-regiao.

### 7.4 Colisao

Uma colisao e registrada quando carros de direcoes conflitantes ocupam o mesmo quadrante ao mesmo tempo.

Esse modelo evita falsos positivos e melhora a explicacao durante a apresentacao, porque deixa claro que o problema nao e "ter muitos carros", e sim "ter acesso concorrente sem coordenacao a um espaco compartilhado".

### 7.5 Variacao entre execucoes

Dois fatores tornam a simulacao mais interessante:

- cada thread pode iniciar com atraso diferente
- cada carro recebe velocidade propria

Por isso, duas execucoes com os mesmos parametros podem produzir resultados diferentes. Essa caracteristica ajuda muito na explicacao do comportamento nao deterministico em sistemas concorrentes.

## 8. Estados dos Carros

Durante a execucao, cada carro pode assumir um dos seguintes estados:

- moving: carro em movimento fora da regiao critica
- in_critical: carro dentro da regiao critica
- collided: carro envolvido em colisao
- finished: carro concluiu a rota

Esses estados aparecem na interface e tambem ajudam a explicar a evolucao da simulacao passo a passo.

## 9. Comunicacao em Tempo Real

O backend envia snapshots do estado da simulacao para o frontend por WebSocket. Isso faz com que a interface seja atualizada continuamente sem precisar recarregar a pagina.

Esse detalhe e muito importante na apresentacao porque mostra que o sistema nao e uma animacao pregravada. O frontend esta refletindo, em tempo real, o estado produzido pelas threads no backend.

## 10. Principais Recursos da Interface

O sistema possui uma interface simples, mas muito eficiente para apresentacao. Entre os recursos mais importantes estao:

- canvas com o cruzamento e os carros
- legenda de estados visuais
- controle de numero de carros
- controle de velocidade da simulacao
- controle de dispersao de partida
- estatisticas agregadas
- tabela com o estado das threads
- log cronologico de eventos

Esses elementos tornam a apresentacao mais fluida porque permitem explicar o sistema em diferentes niveis: visual, tecnico e operacional.

## 11. Pontos Fortes do Projeto

### 11.1 Clareza didatica

O projeto traduz um tema abstrato em uma representacao visual simples de entender.

### 11.2 Boa separacao de responsabilidades

O backend cuida da logica concorrente e o frontend da visualizacao. Isso facilita manutencao, leitura do codigo e explicacao da arquitetura.

### 11.3 Parametrizacao

O usuario pode alterar a quantidade de carros, a velocidade e a dispersao de partida. Isso ajuda a explorar varios cenarios na apresentacao.

### 11.4 Observabilidade

A combinacao de tabela de threads, estatisticas e log de eventos oferece uma visao muito rica do que esta acontecendo internamente.

### 11.5 Potencial de evolucao

O projeto ja esta bem estruturado para servir de base para novas versoes, por exemplo:

- versao com sincronismo
- comparacao entre comportamentos
- novas regras de prioridade
- novos tipos de cruzamento
- metricas adicionais

## 12. Limitacoes Atuais

Todo projeto academico ganha forca quando a equipe sabe apontar tambem suas limitacoes. Neste caso, as principais sao:

- a simulacao representa um cenario didatico, nao um transito real completo
- o frontend depende do backend local rodando na porta configurada
- a deteccao de conflito foi pensada para o modelo do cruzamento atual
- o projeto nao implementa ainda uma versao com sincronismo para comparacao direta
- nao ha persistencia de dados ou historico entre execucoes

Essas limitacoes nao enfraquecem o trabalho. Pelo contrario: mostram que a equipe entende o escopo e sabe onde o projeto pode evoluir.

## 13. Comandos para Rodar o Sistema

### 13.1 Criar ambiente virtual

```powershell
python -m venv .venv
```

### 13.2 Ativar ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

### 13.3 Instalar dependencias

```powershell
pip install -r backend\requirements.txt
```

### 13.4 Iniciar backend

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 13.5 Abrir frontend

Em outra janela do terminal:

```powershell
start .\frontend\index.html
```

## 14. Roteiro de Demonstracao ao Vivo

Uma boa apresentacao nao depende apenas do que o sistema faz, mas de como a equipe mostra isso. Um roteiro simples e eficiente seria:

1. Apresentar o problema teorico: concorrencia e regiao critica.
2. Mostrar a arquitetura geral do sistema.
3. Explicar que cada carro equivale a uma thread.
4. Executar a simulacao com poucos carros.
5. Apontar o log, os estados e as estatisticas.
6. Repetir com mais carros e menor dispersao de partida.
7. Mostrar que os resultados variam entre execucoes.
8. Concluir reforcando por que sistemas concorrentes precisam de sincronizacao.

## 15. Sugestao de Divisao da Apresentacao entre 3 Integrantes

### Integrante 1 - Contexto e objetivo

Pode apresentar:

- o problema da concorrencia
- o que e uma thread
- o que e regiao critica
- por que foi escolhido o exemplo do cruzamento
- objetivo geral e objetivo especifico do projeto

### Integrante 2 - Arquitetura e implementacao

Pode apresentar:

- divisao entre backend e frontend
- papel do FastAPI
- criacao das threads
- estados dos carros
- logica de quadrantes e deteccao de colisao

### Integrante 3 - Demonstracao e conclusao

Pode apresentar:

- execucao pratica do sistema
- leitura dos controles e estatisticas
- interpretacao do log de eventos
- analise dos resultados
- limitacoes e proximos passos

## 16. Perguntas Provaveis e Respostas Curtas

### "Por que usar threads neste projeto?"

Porque o objetivo e representar execucao concorrente real no backend, e nao apenas uma animacao visual.

### "Por que o resultado muda entre uma execucao e outra?"

Porque cada thread pode iniciar em tempos diferentes e com velocidades diferentes, produzindo comportamento nao deterministico.

### "O que o cruzamento representa conceitualmente?"

Representa uma regiao critica, ou seja, uma parte compartilhada do sistema que pode sofrer conflito se varias threads acessarem ao mesmo tempo.

### "Como evitar as colisoes?"

Seria necessario introduzir um mecanismo de sincronizacao para controlar o acesso das threads a area critica.

### "Qual e o principal aprendizado do projeto?"

Que concorrencia sem coordenacao pode gerar conflitos, e que observar isso visualmente ajuda a entender por que sincronizacao e tao importante.

## 17. Como Defender o Projeto com Mais Seguranca

Durante a apresentacao, vale insistir em quatro ideias-chave:

- cada carro nao e apenas um desenho: ele corresponde a uma thread
- o centro do cruzamento representa um recurso compartilhado
- sem sincronismo, duas threads podem acessar a mesma area ao mesmo tempo
- as colisoes nao sao um erro do projeto: sao justamente a demonstracao do conceito estudado

Se a equipe sustentar esses quatro pontos com clareza, a apresentacao tende a ficar muito consistente.

## 18. Conclusao

O projeto "Estudo de Threads" e forte para apresentacao academica porque consegue unir teoria, pratica e visualizacao. Ele mostra de maneira concreta como threads concorrentes podem disputar acesso a uma regiao critica e gerar race condition quando nao existe coordenacao.

Mais do que um simulador visual, o trabalho funciona como uma ponte entre o conceito estudado em sala e o comportamento real de um sistema concorrente. Isso o torna um excelente material para explicacao, demonstracao e discussao em grupo.

## 19. Fechamento Sugerido para a Fala Final

Uma boa frase de encerramento para a equipe seria:

"Nosso projeto mostra, de forma visual e interativa, que concorrencia nao e apenas executar varias tarefas ao mesmo tempo. Sem sincronizacao adequada, o acesso compartilhado pode gerar conflitos reais. O simulador nos permitiu enxergar esse problema acontecendo em tempo real."
