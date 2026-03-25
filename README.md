# Estudo de Threads

Simulador visual de concorrencia usando threads em Python para demonstrar race condition em um cruzamento sem sincronismo.

Projeto academico com foco em visualizacao pratica de concorrencia.

O sistema possui:

- Backend em FastAPI responsavel por iniciar, resetar e controlar a simulacao
- Frontend estatico em HTML, CSS e JavaScript
- Atualizacao em tempo real via WebSocket
- Um carro por thread
- Deteccao de colisao por quadrante na regiao critica do cruzamento

## Resumo do Sistema

Cada carro e executado em uma thread separada no backend. Todos atravessam um cruzamento central que funciona como regiao critica. Como o movimento ocorre sem mecanismo de sincronismo, o projeto evidencia o comportamento concorrente e permite observar colisoes quando dois carros conflitantes ocupam o mesmo quadrante ao mesmo tempo.

O frontend mostra:

- animacao dos carros no canvas
- estado atual de cada thread
- estatisticas da simulacao
- log de eventos em tempo real

## Tecnologias

- Python
- FastAPI
- Uvicorn
- Pydantic
- HTML
- CSS
- JavaScript
- WebSocket

## Estrutura do Projeto

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
`-- README.md
```

## Como a Simulacao Funciona

### Backend

- `backend/main.py`: cria a aplicacao FastAPI, registra CORS, expoe as rotas da API e o WebSocket
- `backend/routes/simulation_routes.py`: define os endpoints de controle da simulacao
- `backend/services/simulation_service.py`: contem a logica principal da simulacao, criacao das threads, movimentacao dos carros, eventos e deteccao de colisao
- `backend/models/car.py`: define os modelos de carro, estado e direcao
- `backend/models/simulation.py`: define as estatisticas agregadas da simulacao

### Regras principais

- cada carro nasce em uma pista fixa
- cada carro recebe velocidade propria
- cada thread pode ter atraso de partida independente
- a regiao critica do cruzamento e dividida em 4 quadrantes
- ocorre colisao quando carros de direcoes conflitantes ocupam o mesmo quadrante ao mesmo tempo
- a ausencia de lock no movimento e intencional para fins didaticos

## Endpoints da API

### `POST /api/start`

Inicia uma nova simulacao.

Exemplo de corpo:

```json
{
  "num_cars": 4,
  "max_delay": 3.5
}
```

### `POST /api/speed`

Atualiza a velocidade global da simulacao.

Exemplo de corpo:

```json
{
  "level": 4
}
```

### `POST /api/reset`

Reseta a simulacao atual.

### `GET /api/state`

Retorna o estado atual da simulacao.

### `GET /ws`

WebSocket usado pelo frontend para receber atualizacoes em tempo real.

## Pre-requisitos

- Python 3.10 ou superior
- `pip` habilitado
- Navegador web moderno

Python 3.11 ou superior e recomendado.

## Como Rodar Pelo Terminal

As instrucoes abaixo usam PowerShell no Windows.

### 1. Entrar na pasta do projeto

```powershell
cd C:\caminho\para\Estudo-de-Threads
```

### 2. Criar ambiente virtual

```powershell
python -m venv .venv
```

Se o comando `python` nao funcionar, tente:

```powershell
py -3 -m venv .venv
```

### 3. Ativar o ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativacao por politica de execucao:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

### 4. Instalar as dependencias do backend

```powershell
pip install -r backend\requirements.txt
```

### 5. Iniciar o servidor FastAPI

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Se estiver usando `py`:

```powershell
cd backend
py -3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

O backend ficara disponivel em:

```text
http://127.0.0.1:8001
```

### 6. Abrir o frontend

Com o backend rodando, abra outra janela do terminal na raiz do projeto e execute:

```powershell
start .\frontend\index.html
``` 

Tambem e possivel abrir manualmente o arquivo `frontend/index.html` no navegador.

## Fluxo de Uso

1. Inicie o backend pelo terminal.
2. Abra o frontend no navegador.
3. Defina a quantidade de carros.
4. Ajuste a velocidade da simulacao.
5. Ajuste a dispersao de partida.
6. Clique em `Iniciar`.
7. Observe a execucao das threads, o log e as colisoes.

## Observacoes Importantes

- O frontend e estatico e depende do backend rodando na porta `8001`
- O projeto foi construido para demonstrar concorrencia sem sincronismo
- Colisoes podem ou nao ocorrer em cada execucao, dependendo do tempo de partida e da velocidade individual de cada thread
- O CORS esta liberado no backend para simplificar a integracao local

## Encerrando o Sistema

- para parar o backend, pressione `Ctrl + C` no terminal onde o Uvicorn esta rodando
- para sair do ambiente virtual, execute:

```powershell
deactivate
```

## Objetivo Academico

Este projeto e apropriado para estudos de:

- threads
- concorrencia
- regiao critica
- race condition
- sincronizacao
- visualizacao de comportamento concorrente
