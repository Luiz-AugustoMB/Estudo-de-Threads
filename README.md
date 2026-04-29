# Estudo de Threads — Sincronismo em Cruzamento de Vias

Simulador visual de concorrencia e sincronismo de threads em Python. Cada veiculo e executado como uma thread independente que precisa atravessar um cruzamento central protegido por semaforos por quadrante.

Projeto academico com foco em visualizacao pratica de concorrencia, exclusao mutua e algoritmos de escalonamento.

## Apresentacoes

O projeto possui duas paginas com propositos distintos:

| Pagina | Proposito |
|---|---|
| `index.html` | Simulacao principal com modo sincronizado (semaforos) e modo livre (colisao) |
| `index2.html` | Comparacao lado a lado entre os algoritmos de escalonamento FCFS e SJF |

## O que o Sistema Demonstra

### Conceitos de Threads

- Cada veiculo e uma thread Python (`threading.Thread`) rodando de forma concorrente
- A regiao critica e o cruzamento central, dividido em 4 quadrantes (Q1, Q2, Q3, Q4)
- O acesso exclusivo a cada quadrante e controlado por `QuadrantScheduler` — uma estrutura com fila de prioridade que implementa os algoritmos FCFS e SJF

### Modos de Simulacao (index.html)

**Semaforos ON** — modo sincronizado:
- Cada quadrante possui um semaforo proprio
- O veiculo reserva os dois quadrantes do seu trajeto antes de entrar
- A ordem de atendimento segue o algoritmo de escalonamento ativo
- Nenhuma colisao ocorre

**Semaforos OFF** — modo livre:
- Veiculos entram na regiao critica sem coordenacao
- Colisoes ocorrem quando dois veiculos de direcoes conflitantes ocupam o mesmo quadrante
- Demonstra o que acontece sem exclusao mutua (race condition)

### Algoritmos de Escalonamento (index2.html)

**FCFS — First Come First Served:**
- Atende os veiculos na ordem de chegada a fila de espera
- Chave de prioridade: `(arrival_time, seq)`

**SJF — Shortest Job First:**
- Atende primeiro o veiculo com menor tempo estimado de travessia
- Tempo de job: `120px / velocidade` — veiculos mais rapidos tem menor job e passam primeiro
- Chave de prioridade: `(job_time, arrival_time, seq)`

As tabelas de cada modo permanecem visiveis apos a simulacao para comparacao direta de tempo total e tempo de espera por veiculo.

## Estrutura do Projeto

```text
Estudo-de-Threads/
|-- backend/
|   |-- main.py
|   |-- requirements.txt
|   |-- models/
|   |   |-- car.py
|   |   `-- simulation.py
|   |-- routes/
|   |   `-- simulation_routes.py
|   `-- services/
|       `-- simulation_service.py
|-- frontend/
|   |-- index.html       <- simulacao principal (sync ON/OFF)
|   |-- index2.html      <- comparacao FCFS vs SJF
|   |-- script.js
|   |-- script2.js
|   `-- style.css
`-- README.md
```

## Como a Simulacao Funciona

### Geracao dos Veiculos

A cada inicio sao gerados 8 veiculos aleatorios:
- Entre 1 e 4 caminhoes, o restante sao carros
- Direcoes sortidas entre Norte, Sul, Leste e Oeste
- Velocidades aleatorias dentro de faixas fixas por tipo
- Carros: 4.0 a 9.5 px/passo
- Caminhoes: 2.0 a 5.5 px/passo
- Atraso de partida aleatorio para evitar chegadas identicas

### Regiao Critica e Quadrantes

O cruzamento ocupa a area central de 120x120px do canvas (500x500px). Ela e dividida em 4 quadrantes:

| Quadrante | Posicao | Direcoes que passam |
|---|---|---|
| Q1 | superior esquerdo | Norte (↓) e Oeste (→) |
| Q2 | superior direito | Sul (↑) e Oeste (→) |
| Q3 | inferior esquerdo | Norte (↓) e Leste (←) |
| Q4 | inferior direito | Sul (↑) e Leste (←) |

Cada veiculo reserva dois quadrantes consecutivos antes de entrar. A ordem de aquisicao e sempre do menor indice para o maior (previne deadlock). Ao atingir o segundo quadrante, o primeiro e liberado imediatamente (handoff progressivo).

### Escalonador de Quadrante

`QuadrantScheduler` substitui um `Semaphore(1)` simples. Internamente mantem um heap de prioridade com os veiculos na fila. Ao liberar um quadrante, o proximo veiculo com maior prioridade (menor chave) e desbloqueado automaticamente via `Condition.notify_all()`.

### Deteccao de Colisao (modo sem sincronismo)

Apos cada passo de movimento, o servico verifica se dois ou mais veiculos de direcoes conflitantes estao no mesmo quadrante. Se sim, ambos recebem o estado `COLLIDED` e uma explosao e exibida no canvas.

## Endpoints da API

### `POST /api/start`

Inicia uma nova simulacao com 8 veiculos aleatorios.

Corpo (todos os campos sao opcionais):

```json
{
  "sync_enabled": true,
  "scheduling_mode": "fcfs"
}
```

| Campo | Tipo | Padrao | Descricao |
|---|---|---|---|
| `sync_enabled` | bool | `true` | `true` ativa semaforos; `false` permite colisao |
| `scheduling_mode` | string | `"fcfs"` | `"fcfs"` ou `"sjf"` |

### `POST /api/reset`

Interrompe e limpa a simulacao atual.

### `GET /api/state`

Retorna o estado atual da simulacao (usado internamente pelo WebSocket).

### `GET /ws`

WebSocket com atualizacoes a 20 fps. Retorna JSON com:

```json
{
  "running": true,
  "cars": [...],
  "stats": {
    "total_vehicles": 8,
    "total_crossings": 3,
    "total_collisions": 0,
    "sync_enabled": true,
    "scheduling_mode": "fcfs",
    "quadrants": {
      "Q1": { "free": true, "holder": null },
      "Q2": { "free": false, "holder": 4 },
      "Q3": { "free": true, "holder": null },
      "Q4": { "free": true, "holder": null }
    }
  },
  "events": [...]
}
```

## Pre-requisitos

- Python 3.10 ou superior (3.11+ recomendado)
- `pip` habilitado
- Navegador web moderno com suporte a Canvas e WebSocket

## Como Rodar

### 1. Entrar na pasta do projeto

```powershell
cd C:\caminho\para\Estudo-de-Threads
```

### 2. Criar e ativar ambiente virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativacao por politica de execucao:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```powershell
pip install -r backend\requirements.txt
```

### 4. Iniciar o servidor

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

O backend ficara disponivel em `http://127.0.0.1:8001`.

### 5. Abrir o frontend

```powershell
start .\frontend\index.html
```

Para a apresentacao de escalonamento:

```powershell
start .\frontend\index2.html
```

Tambem e possivel abrir os arquivos diretamente no navegador.

## Fluxo de Uso

### Simulacao Principal (index.html)

1. Inicie o backend
2. Abra `index.html`
3. Escolha o modo: **Semaforos ON** (sincronizado) ou **Semaforos OFF** (colisao livre)
4. Clique em **Iniciar**
5. Observe as threads, o log de eventos e os semaforos por quadrante
6. Clique em **Reiniciar** para uma nova frota aleatoria

### Comparacao FCFS vs SJF (index2.html)

1. Inicie o backend
2. Abra `index2.html`
3. Selecione **FCFS** e clique em **Iniciar** — a tabela FCFS e preenchida
4. Apos o termino, o botao muda automaticamente para **SJF**
5. Clique em **Iniciar** novamente — a tabela SJF e preenchida
6. Compare lado a lado o tempo total e o tempo de espera de cada veiculo
7. **Reiniciar** limpa apenas a simulacao atual; as tabelas permanecem para comparacao

## Observacoes

- O frontend e estatico e depende do backend rodando na porta `8001`
- O CORS esta liberado no backend para simplificar o uso local
- As velocidades dos veiculos sao aleatorias a cada inicio, por isso os resultados de FCFS e SJF variam entre execucoes
- No modo SJF, veiculos mais rapidos tem prioridade; no FCFS, o primeiro a chegar a fila passa primeiro independente da velocidade

## Encerrando

Para parar o backend, pressione `Ctrl + C` no terminal do Uvicorn.

Para sair do ambiente virtual:

```powershell
deactivate
```

## Objetivo Academico

Este projeto e adequado para estudos de:

- threads e concorrencia
- regiao critica e exclusao mutua
- semaforos e locks
- race condition
- algoritmos de escalonamento (FCFS e SJF)
- visualizacao de comportamento concorrente em tempo real
