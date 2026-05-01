# Módulo de fila de prioridade (min-heap) para o escalonador FCFS/SJF
import heapq
# Módulo de threads para executar cada veículo em paralelo
import threading
# Módulo de tempo para controlar delays e medir duração das travessias
import time
# Tipo Optional para indicar que um valor pode ser None
from typing import Optional

# Modelos de domínio: carro, estado, direção e tipo de veículo
from models.car import Car, CarState, Direction, VehicleType
# Modelo de estatísticas da simulação (colisões, travessias, etc.)
from models.simulation import SimulationStats

# Largura do canvas em pixels
CANVAS_W = 500
# Altura do canvas em pixels
CANVAS_H = 500

# Limites horizontais da região crítica (cruzamento) em pixels
CRIT_X1, CRIT_X2 = 190, 310
# Limites verticais da região crítica (cruzamento) em pixels
CRIT_Y1, CRIT_Y2 = 190, 310
# Centro geométrico do cruzamento
CRIT_CX, CRIT_CY = 250, 250

# Coordenadas das faixas de tráfego no sentido NW (Norte/Oeste) — pista A e B
LANE_NW_A = 216
LANE_NW_B = 224
# Coordenadas das faixas de tráfego no sentido SE (Sul/Leste) — pista A e B
LANE_SE_A = 276
LANE_SE_B = 284

# Intervalo de tempo (segundos) entre cada passo de movimento dos veículos (~25 fps)
STEP_DELAY = 0.04
# Número máximo de eventos que o log da simulação mantém em memória
MAX_EVENTS = 200
# Quantidade total de veículos gerados por simulação
TOTAL_VEHICLES = 8
# Quantidade mínima de caminhões garantida por simulação
MIN_TRUCKS = 1
# Quantidade máxima de caminhões permitida por simulação
MAX_TRUCKS = 4
# Faixa de velocidade dos carros em pixels por passo
CAR_SPEED_RANGE = (4.0, 9.5)
# Faixa de velocidade dos caminhões em pixels por passo (mais lentos)
TRUCK_SPEED_RANGE = (2.0, 5.5)
# Deslocamento inicial base (em pixels) antes de entrar no canvas — afasta veículos na largada
BASE_STAGGER_RANGE = (0.0, 60.0)
# Distância fixa entre veículos na mesma faixa para evitar sobreposição inicial
STAGGER_GAP = 140.0
# Variação aleatória extra adicionada ao gap entre veículos na mesma faixa
STAGGER_VARIATION = 35.0

# Tamanho em pixels da travessia pela região crítica — usado pelo SJF para calcular tempo de cruzamento
INTERSECTION_SIZE = float(CRIT_X2 - CRIT_X1)  # 120 px

# Mapeia cada direção de entrada para as coordenadas das faixas disponíveis nela
LANES_BY_DIRECTION: dict[Direction, tuple[float, ...]] = {
    Direction.NORTH: (float(LANE_NW_A), float(LANE_NW_B)),   # Norte usa faixas NW
    Direction.SOUTH: (float(LANE_SE_A), float(LANE_SE_B)),   # Sul usa faixas SE
    Direction.WEST: (float(LANE_NW_A), float(LANE_NW_B)),    # Oeste usa faixas NW
    Direction.EAST: (float(LANE_SE_A), float(LANE_SE_B)),    # Leste usa faixas SE
}

# Especificações fixas dos veículos: garante que todas as simulações iniciem com
# os mesmos veículos, nas mesmas posições e velocidades — apenas o escalonador varia.
# Formato de cada entrada: (direção, velocidade, tipo, faixa, stagger_inicial)
# Staggers calculados para que o veículo LENTO de cada par conflitante chegue ao
# cruzamento ~5 passos ANTES do veículo rápido. Isso garante que FCFS e SJF tomem
# decisões opostas: FCFS serve o lento primeiro (chegou antes), SJF serve o rápido
# primeiro (menor job = 120/vel). Fórmula: stagger = vel × t_chegada − 190.
#
# Conflitos planejados (Q1 = N×W, Q4 = S×E):
#   W-truck(vel=3) chega t=70 → N-car(vel=7)  chega t=75  (Q1, faixa 224×216)
#   N-truck(vel=4.5) chega t=47 → W-car(vel=6) chega t=52  (Q1, faixa 224×216)
#   S-truck(vel=3.5) chega t=60 → E-car(vel=9)  chega t=65  (Q4, faixa 284×276)
#   E-car(vel=5)   chega t=42 → S-car(vel=8.5) chega t=47  (Q4, faixa 284×276)
FIXED_VEHICLE_SPECS: list[tuple[Direction, float, VehicleType, float, float]] = [
    # stagger = vel × t_chegada − 190
    (Direction.NORTH, 7.0, VehicleType.CAR,   216.0, 335.0),  # chega t=75  (7×75−190)
    (Direction.NORTH, 4.5, VehicleType.TRUCK, 224.0,  20.0),  # chega t=47  (4.5×47−190≈21, usa 20)
    (Direction.SOUTH, 8.5, VehicleType.CAR,   276.0, 210.0),  # chega t=47  (8.5×47−190)
    (Direction.SOUTH, 3.5, VehicleType.TRUCK, 284.0,  20.0),  # chega t=60  (3.5×60−190)
    (Direction.WEST,  6.0, VehicleType.CAR,   216.0, 122.0),  # chega t=52  (6×52−190)
    (Direction.WEST,  3.0, VehicleType.TRUCK, 224.0,  20.0),  # chega t=70  (3×70−190)
    (Direction.EAST,  9.0, VehicleType.CAR,   276.0, 395.0),  # chega t=65  (9×65−190)
    (Direction.EAST,  5.0, VehicleType.CAR,   284.0,  20.0),  # chega t=42  (5×42−190)
]

# Rótulos legíveis para exibição no log: tipo de veículo → texto em português
VEHICLE_LABEL = {VehicleType.CAR: "Carro", VehicleType.TRUCK: "Caminhao"}
# Rótulos legíveis para exibição no log: direção → descrição do trajeto
DIR_LABEL = {
    Direction.NORTH: "topo->base",
    Direction.SOUTH: "base->topo",
    Direction.WEST: "esq->dir",
    Direction.EAST: "dir->esq",
}

# Define quais dois quadrantes cada direção percorre ao cruzar o cruzamento
PATH_QUADRANTS: dict[Direction, tuple[str, str]] = {
    Direction.NORTH: ("Q1", "Q3"),  # Norte entra por Q1 e sai por Q3
    Direction.SOUTH: ("Q4", "Q2"),  # Sul entra por Q4 e sai por Q2
    Direction.WEST: ("Q1", "Q2"),   # Oeste entra por Q1 e sai por Q2
    Direction.EAST: ("Q4", "Q3"),   # Leste entra por Q4 e sai por Q3
}

# Define quais direções de veículo podem causar conflito em cada quadrante (para detecção de colisão)
QUADRANT_DIRS: dict[str, set[Direction]] = {
    "Q1": {Direction.NORTH, Direction.WEST},   # Q1 é compartilhado por Norte e Oeste
    "Q2": {Direction.SOUTH, Direction.WEST},   # Q2 é compartilhado por Sul e Oeste
    "Q3": {Direction.NORTH, Direction.EAST},   # Q3 é compartilhado por Norte e Leste
    "Q4": {Direction.SOUTH, Direction.EAST},   # Q4 é compartilhado por Sul e Leste
}

# Lista ordenada de nomes dos quadrantes (Q1..Q4)
QUADRANT_NAMES = ("Q1", "Q2", "Q3", "Q4")
# Índice numérico de cada quadrante — usado para ordenar aquisições e evitar deadlock
QUADRANT_INDEX = {name: idx for idx, name in enumerate(QUADRANT_NAMES)}


def _build_start_pos(
    direction: Direction,
    lane_coord: float,
    stagger: float,
) -> tuple[float, float]:
    # Retorna a posição inicial (x, y) de um veículo fora do canvas de acordo com sua direção
    if direction == Direction.NORTH:
        # Veículos do Norte começam acima do canvas (y negativo)
        return (lane_coord, -stagger)
    if direction == Direction.SOUTH:
        # Veículos do Sul começam abaixo do canvas
        return (lane_coord, CANVAS_H + stagger)
    if direction == Direction.WEST:
        # Veículos do Oeste começam à esquerda do canvas
        return (-stagger, lane_coord)
    # Veículos do Leste começam à direita do canvas
    return (CANVAS_W + stagger, lane_coord)


def _direction_delta(direction: Direction) -> tuple[float, float]:
    # Retorna o vetor unitário de movimento (dx, dy) para a direção informada
    return {
        Direction.NORTH: (0.0, 1.0),   # Norte: desce no canvas (y cresce)
        Direction.SOUTH: (0.0, -1.0),  # Sul: sobe no canvas (y decresce)
        Direction.WEST: (1.0, 0.0),    # Oeste: move para direita (x cresce)
        Direction.EAST: (-1.0, 0.0),   # Leste: move para esquerda (x decresce)
    }[direction]


def _in_critical(x: float, y: float) -> bool:
    # Retorna True se o ponto (x, y) está dentro da região crítica do cruzamento
    return CRIT_X1 <= x <= CRIT_X2 and CRIT_Y1 <= y <= CRIT_Y2


def _next_in_critical(
    x: float,
    y: float,
    dx: float,
    dy: float,
    speed: float,
) -> bool:
    # Retorna True se o próximo passo do veículo o levaria para dentro da região crítica
    return _in_critical(x + dx * speed, y + dy * speed)


def _has_exited(car: Car) -> bool:
    # Retorna True se o veículo já saiu da região crítica (cruzou para o outro lado)
    if car.direction == Direction.NORTH:
        return car.y > CRIT_Y2   # Norte: saiu quando y passa do limite inferior
    if car.direction == Direction.SOUTH:
        return car.y < CRIT_Y1   # Sul: saiu quando y passa do limite superior
    if car.direction == Direction.WEST:
        return car.x > CRIT_X2   # Oeste: saiu quando x passa do limite direito
    return car.x < CRIT_X1       # Leste: saiu quando x passa do limite esquerdo


def _out_of_bounds(car: Car) -> bool:
    # Retorna True se o veículo saiu completamente do canvas (pode ser removido da simulação)
    if car.direction == Direction.NORTH:
        return car.y > CANVAS_H + 60   # Norte: desapareceu pela borda inferior
    if car.direction == Direction.SOUTH:
        return car.y < -60             # Sul: desapareceu pela borda superior
    if car.direction == Direction.WEST:
        return car.x > CANVAS_W + 60  # Oeste: desapareceu pela borda direita
    return car.x < -60                 # Leste: desapareceu pela borda esquerda


def _which_quadrant(x: float, y: float) -> str:
    # Retorna o nome do quadrante ("Q1"–"Q4") em que o ponto (x, y) se encontra, ou "" se fora da região crítica
    if not _in_critical(x, y):
        return ""  # Ponto fora da região crítica — não pertence a nenhum quadrante

    left = x <= CRIT_CX   # True se o ponto está na metade esquerda do cruzamento
    top = y <= CRIT_CY    # True se o ponto está na metade superior do cruzamento
    if left and top:
        return "Q1"   # Superior esquerdo
    if not left and top:
        return "Q2"   # Superior direito
    if left:
        return "Q3"   # Inferior esquerdo
    return "Q4"        # Inferior direito


# ── Escalonador de quadrante ──────────────────────────────────────────────────

class QuadrantScheduler:
    """Portão de ocupação única com fila de prioridade.

    FCFS – atende na ordem de chegada à espera.
    SJF  – atende primeiro quem tem menor tempo de travessia (INTERSECTION_SIZE / speed).
    """

    def __init__(self, mode: str) -> None:
        # Modo de escalonamento: "fcfs" (ordem de chegada) ou "sjf" (menor job primeiro)
        self._mode = mode
        # Variável de condição para sincronizar threads que aguardam o portão
        self._cv = threading.Condition()
        # ID do veículo que atualmente ocupa este quadrante (None = livre)
        self._holder: Optional[int] = None
        # Fila de prioridade (heap) com os veículos aguardando o portão
        self._waiters: list[tuple] = []
        # Contador de sequência global para desempate entre chegadas simultâneas
        self._seq = 0

    @property
    def holder(self) -> Optional[int]:
        # Expõe o ID do ocupante atual (somente leitura)
        return self._holder








#MODOS DE ESCALONAMENTO
    def acquire(
        self,
        car_id: int,
        speed: float,
        arrival_time: float,
        is_active: callable,
    ) -> bool:
        """Bloqueia até este veículo adquirir o portão.
        Retorna False se a simulação terminar enquanto espera."""
        with self._cv:
            # Incrementa e captura a sequência de chegada deste veículo
            self._seq += 1
            seq = self._seq
            if self._mode == "fcfs":
                # ============================================================
                # ALGORITMO FCFS — First-Come, First-Served
                # Escalonamento NÃO PREEMPTIVO baseado na ordem de chegada.
                # O veículo que chegou primeiro à fila de espera é o primeiro
                # a receber acesso ao quadrante (portão).
                # Chave de prioridade: (arrival_time, seq)
                #   → arrival_time: instante em que o veículo começou a esperar
                #   → seq: nº de sequência global para desempate entre chegadas
                #          simultâneas (garante FIFO estrito)
                # ============================================================
                key = (arrival_time, seq)
            else:  # sjf
                # ============================================================
                # ALGORITMO SJF — Shortest Job First
                # Escalonamento NÃO PREEMPTIVO que prioriza o veículo com o
                # menor tempo estimado de travessia pela região crítica.
                # O "job" de cada veículo é calculado como:
                #   job_time = INTERSECTION_SIZE / speed  (passos necessários)
                # Chave de prioridade: (job_time, arrival_time, seq)
                #   → job_time: estimativa do tempo de ocupação do quadrante
                #   → arrival_time: desempate pelo critério FCFS quando dois
                #                   veículos têm o mesmo job_time
                #   → seq: desempate final por ordem de chegada ao heap
                # ============================================================
                job_time = INTERSECTION_SIZE / speed
                key = (job_time, arrival_time, seq)

            # Insere o veículo na fila de espera com sua chave de prioridade
            heapq.heappush(self._waiters, (key, car_id))





#SEMAFARO ESTA AQUI
            while True:
                if not is_active():
                    # Simulação encerrada: remove este veículo da fila e acorda os demais
                    self._waiters = [(k, c) for k, c in self._waiters if c != car_id]
                    heapq.heapify(self._waiters)
                    self._cv.notify_all()
                    return False  # Sinaliza que a aquisição falhou por encerramento

                if (
                    self._holder is None            # Portão está livre
                    and self._waiters               # Há alguém esperando
                    and self._waiters[0][1] == car_id  # Este veículo é o primeiro da fila
                ):
                    # Remove o veículo da fila e concede o portão a ele
                    heapq.heappop(self._waiters)
                    self._holder = car_id
                    return True  # Aquisição bem-sucedida

                # Portão ocupado ou este veículo não é o próximo: aguarda com timeout de segurança
                self._cv.wait(timeout=0.05)





    def release(self, car_id: int) -> None:
        with self._cv:
            # Só libera se este veículo for realmente o ocupante atual
            if self._holder == car_id:
                self._holder = None
            # Acorda todos os waiters para que reavalifiquem a fila
            self._cv.notify_all()

    def wake_all(self) -> None:
        """Acorda todos os esperadores para que verifiquem is_active() e abortem."""
        with self._cv:
            # Notifica todas as threads bloqueadas em acquire() para que saiam ao detectar is_active() == False
            self._cv.notify_all()


# ── Serviço de simulação ──────────────────────────────────────────────────────

class SimulationService:
    def __init__(self) -> None:
        # Dicionário de veículos ativos: id → objeto Car
        self.cars: dict[int, Car] = {}
        # Estatísticas acumuladas da simulação atual
        self.stats = SimulationStats()
        # Flag que indica se a simulação está em andamento
        self.running = False
        # Flag que ativa/desativa a sincronização (semáforos); False = modo colisão livre
        self.sync_enabled = True
        # Modo de escalonamento padrão ao iniciar
        self._scheduling_mode = "fcfs"

        # Contador de versão da simulação — evita que threads de simulações antigas interfiram na atual
        self._sim_id = 0
        # Timestamp do início da simulação atual (para calcular tempo relativo no log)
        self._sim_start = 0.0
        # Portões de ocupação por quadrante: nome → QuadrantScheduler
        self._quadrant_gates: dict[str, QuadrantScheduler] = {}
        # Ocupante atual de cada quadrante: nome → car_id ou None
        self._quadrant_holders: dict[str, Optional[int]] = {}
        # Conjunto de IDs de veículos que já colidiram (evita registrar a mesma colisão duas vezes)
        self._collided_set: set[int] = set()
        # Contador total de travessias concluídas na simulação atual
        self._total_crossings = 0
        # Lock principal para proteger estado compartilhado (holders, crossings, stats)
        self._lock = threading.Lock()
        # Lock exclusivo para a seção crítica de detecção de colisão
        self._collision_lock = threading.Lock()
        # Lock para proteger a lista de eventos do log
        self._events_lock = threading.Lock()
        # Lista de eventos registrados durante a simulação
        self.events: list[dict] = []
        # Inicializa os portões e holders de quadrante com valores limpos
        self._reset_quadrant_control()

    # ── API pública ───────────────────────────────────────────────────────────

    def start(self, sync_enabled: bool = True, scheduling_mode: str = "fcfs") -> None:
        if self.running:
            # Se já existe uma simulação rodando, reinicia antes de começar a nova
            self.reset()
            time.sleep(0.15)  # Pequena pausa para garantir que as threads antigas finalizem

        # Incrementa o ID de simulação para invalidar threads da versão anterior
        self._sim_id += 1
        sim_id = self._sim_id
        # Armazena configurações da nova simulação
        self.sync_enabled = sync_enabled
        self._scheduling_mode = scheduling_mode
        self._sim_start = time.time()
        self.running = True
        self._reset_quadrant_control()    # Reseta portões de quadrante
        self._collided_set = set()        # Limpa registro de colisões
        self._total_crossings = 0         # Zera contador de travessias
        self.events = []                  # Limpa log de eventos
        self.cars = {}                    # Remove todos os veículos anteriores

        # Gera a frota aleatória com direções, velocidades, tipos e posições
        generated_vehicles = self._generate_vehicle_specs()
        now = time.time()
        for i, (direction, speed, vtype, lane_coord, stagger) in enumerate(generated_vehicles):
            # Calcula a posição inicial fora do canvas para este veículo
            sx, sy = _build_start_pos(direction, float(lane_coord), float(stagger))
            # Cria o objeto Car e o armazena no dicionário
            self.cars[i] = Car(
                id=i,
                direction=direction,
                vehicle_type=vtype,
                x=sx,
                y=sy,
                speed=float(speed),
                lane_coord=float(lane_coord),
                stagger=float(stagger),
                crossing_start=now,
            )
            # Registra o evento de criação deste veículo no log
            self._log(
                "spawn",
                i,
                (
                    f"{VEHICLE_LABEL[vtype]} {i} gerado em {DIR_LABEL[direction]} | "
                    f"pista={lane_coord:.0f} | vel={speed:.1f} | atraso={stagger:.0f}px"
                ),
            )

        # Texto descritivo do modo de operação para o log de início
        mode_text = (
            f"semaforos ON - escalonamento {scheduling_mode.upper()}"
            if sync_enabled
            else "semaforos OFF - colisao livre"
        )
        # Inicializa as estatísticas com o total de veículos gerados
        self.stats = SimulationStats(total_vehicles=len(self.cars))
        self._log("start", None, f"Simulacao iniciada - frota aleatoria | {mode_text}")

        
        # CRIA TRAD 

        for car_id in self.cars:
            threading.Thread(
                target=self._vehicle_thread,
                args=(car_id, sim_id, sync_enabled),
                daemon=True,  # Thread encerra automaticamente quando o processo principal terminar
            ).start()




    def reset(self) -> None:
        # Invalida a simulação atual incrementando o ID de versão
        self._sim_id += 1
        # Sinaliza para todas as threads que a simulação parou
        self.running = False
        # Acorda threads bloqueadas nos portões de quadrante para que possam encerrar
        for gate in self._quadrant_gates.values():
            gate.wake_all()
        # Limpa todos os dados de estado da simulação
        self.cars = {}
        self.stats = SimulationStats()
        self._total_crossings = 0
        self._collided_set = set()
        self._reset_quadrant_control()
        with self._events_lock:
            self.events = []

    def get_state(self) -> dict:
        # Captura snapshot thread-safe do estado dos quadrantes e estatísticas
        with self._lock:
            crossings = self._total_crossings
            collisions = self.stats.total_collisions
            # Monta dicionário indicando se cada quadrante está livre ou ocupado
            quadrants = {
                name: {"free": holder is None, "holder": holder}
                for name, holder in self._quadrant_holders.items()
            }

        # Captura snapshot thread-safe da lista de eventos
        with self._events_lock:
            events_snap = list(self.events)

        # Retorna o estado completo da simulação para o frontend
        return {
            "running": self.running,
            "cars": [c.to_dict() for c in list(self.cars.values())],  # Serializa cada carro
            "stats": {
                "total_vehicles": self.stats.total_vehicles,
                "total_crossings": crossings,
                "total_collisions": collisions,
                "mode": "sync" if self.sync_enabled else "collision",
                "sync_enabled": self.sync_enabled,
                "scheduling_mode": self._scheduling_mode,
                "quadrants": quadrants,
            },
            "events": events_snap,
        }

    # ── Threads dos veículos ──────────────────────────────────────────────────

    def _vehicle_thread(self, car_id: int, sim_id: int, sync_enabled: bool) -> None:
        # Ponto de entrada da thread de cada veículo — decide qual modo de movimentação usar
        if sync_enabled:
            # Modo sincronizado: veículo aguarda portão antes de entrar no cruzamento
            self._vehicle_thread_sync(car_id, sim_id)
            return
        # Modo colisão livre: veículo entra sem aguardar
        self._vehicle_thread_collision(car_id, sim_id)

    def _vehicle_thread_sync(self, car_id: int, sim_id: int) -> None:
        # Recupera o objeto Car; se não existir, encerra a thread imediatamente
        car = self.cars.get(car_id)
        if car is None:
            return
        # Vetor de movimento do veículo (dx, dy)
        dx, dy = _direction_delta(car.direction)
        # Os dois quadrantes que este veículo precisa atravessar
        first_quadrant, second_quadrant = PATH_QUADRANTS[car.direction]
        # Lista dos quadrantes atualmente reservados por este veículo
        held_quadrants: list[str] = []
        # Rótulo para uso nos logs
        lbl = f"{VEHICLE_LABEL[car.vehicle_type]} {car_id} ({DIR_LABEL[car.direction]})"

        while self.running and self._sim_id == sim_id:
            if not held_quadrants and _next_in_critical(car.x, car.y, dx, dy, car.speed):
                # Veículo está prestes a entrar na região crítica e ainda não reservou quadrantes
                self._start_waiting(car)  # Marca como aguardando e registra horário de espera
                self._log(
                    "waiting",
                    car_id,
                    f"{lbl} aguardando {first_quadrant} + {second_quadrant}",
                )

                # Tenta adquirir os dois quadrantes (bloqueia até conseguir ou simulação encerrar)
                acquired_quadrants = self._acquire_quadrants(
                    car_id=car_id,
                    quadrants=(first_quadrant, second_quadrant),
                    speed=car.speed,
                    arrival_time=car.waiting_since,
                    sim_id=sim_id,
                )
                if not acquired_quadrants:
                    # Simulação encerrada enquanto aguardava — encerra a thread
                    self._stop_waiting(car)
                    return

                held_quadrants = list(acquired_quadrants)
                self._stop_waiting(car)           # Acumula tempo de espera e limpa o marcador
                car.state = CarState.IN_CRITICAL  # Atualiza estado visual do veículo
                self._log(
                    "enter",
                    car_id,
                    f"{lbl} reservou {first_quadrant} + {second_quadrant} e entrou",
                )

            # Avança o veículo um passo na direção configurada
            car.x += dx * car.speed
            car.y += dy * car.speed

            if _in_critical(car.x, car.y):
                # Veículo está dentro do cruzamento: atualiza estado e quadrante atual
                car.state = CarState.IN_CRITICAL
                car.quadrant = _which_quadrant(car.x, car.y)
            else:
                # Veículo saiu do cruzamento: limpa quadrante e volta ao estado MOVING
                car.quadrant = ""
                if car.state == CarState.IN_CRITICAL:
                    car.state = CarState.MOVING

            if (
                len(held_quadrants) == 2
                and car.quadrant == second_quadrant    # Entrou no segundo quadrante
                and first_quadrant in held_quadrants   # Ainda segura o primeiro
            ):
                # Libera o primeiro quadrante (handoff) assim que o veículo avança para o segundo
                self._release_quadrant(car_id, first_quadrant)
                held_quadrants.remove(first_quadrant)
                self._log(
                    "handoff",
                    car_id,
                    f"{lbl} liberou {first_quadrant} e manteve {second_quadrant}",
                )

            if held_quadrants and _has_exited(car):
                # Veículo saiu da região crítica: libera todos os quadrantes restantes
                self._release_quadrants(car_id, tuple(held_quadrants))
                held_quadrants = []
                car.state = CarState.MOVING
                self._log("exit", car_id, f"{lbl} saiu e liberou o trajeto")

            if _out_of_bounds(car):
                # Veículo saiu completamente do canvas: libera recursos e finaliza
                if held_quadrants:
                    self._release_quadrants(car_id, tuple(held_quadrants))
                self._finish_car(car_id, lbl)
                return

            # Aguarda antes do próximo passo para controlar a velocidade da animação
            time.sleep(STEP_DELAY)

    def _vehicle_thread_collision(self, car_id: int, sim_id: int) -> None:
        # Recupera o objeto Car; se não existir, encerra a thread
        car = self.cars.get(car_id)
        if car is None:
            return
        dx, dy = _direction_delta(car.direction)
        lbl = f"{VEHICLE_LABEL[car.vehicle_type]} {car_id} ({DIR_LABEL[car.direction]})"

        while self.running and self._sim_id == sim_id:
            if car.state == CarState.COLLIDED:
                # Veículo já colidiu em tick anterior — encerra a thread
                return

            # Salva o quadrante anterior para detectar mudança de quadrante (handoff)
            previous_quadrant = car.quadrant
            # Avança o veículo sem nenhum bloqueio
            car.x += dx * car.speed
            car.y += dy * car.speed

            # Verifica em qual quadrante o veículo se encontra após o movimento
            current_quadrant = _which_quadrant(car.x, car.y)
            if current_quadrant:
                if car.state != CarState.IN_CRITICAL:
                    # Primeira entrada na região crítica neste percurso
                    car.state = CarState.IN_CRITICAL
                    car.quadrant = current_quadrant
                    self._log(
                        "enter",
                        car_id,
                        f"{lbl} entrou em {current_quadrant} sem sincronizacao",
                    )
                else:
                    # Já estava no cruzamento — apenas atualiza o quadrante atual
                    car.quadrant = current_quadrant
                    if previous_quadrant and previous_quadrant != current_quadrant:
                        # Mudou de quadrante dentro do cruzamento (handoff sem reserva)
                        self._log(
                            "handoff",
                            car_id,
                            f"{lbl} avancou de {previous_quadrant} para {current_quadrant}",
                        )

                # Verifica se há colisão com outro veículo neste quadrante
                self._check_collision(current_quadrant)
                if car.state == CarState.COLLIDED:
                    # Colisão detectada neste tick — encerra a thread
                    return
            else:
                # Veículo não está no cruzamento
                car.quadrant = ""
                if car.state == CarState.IN_CRITICAL:
                    # Acabou de sair da região crítica sem colidir
                    car.state = CarState.MOVING
                    self._log("exit", car_id, f"{lbl} cruzou sem colisao")

            if _out_of_bounds(car):
                # Veículo saiu do canvas — finaliza sem liberar portões (modo sem sincronização)
                self._finish_car(car_id, lbl)
                return

            time.sleep(STEP_DELAY)

    # ── Controle de quadrantes ────────────────────────────────────────────────

    def _reset_quadrant_control(self) -> None:
        # Recria os portões de cada quadrante com o modo de escalonamento atual
        self._quadrant_gates = {
            name: QuadrantScheduler(self._scheduling_mode) for name in QUADRANT_NAMES
        }
        # Marca todos os quadrantes como livres (sem ocupante)
        self._quadrant_holders = {name: None for name in QUADRANT_NAMES}

    def _acquire_quadrants(
        self,
        car_id: int,
        quadrants: tuple[str, str],
        speed: float,
        arrival_time: float,
        sim_id: int,
    ) -> tuple[str, ...]:
        """Adquire os dois quadrantes em ordem (previne deadlock).
        O escalonador (FCFS ou SJF) decide a ordem de atendimento."""
        # Ordena os quadrantes por índice fixo para garantir ordem de aquisição consistente (previne deadlock)
        ordered = tuple(sorted(quadrants, key=QUADRANT_INDEX.__getitem__))
        # Lambda que verifica se a simulação ainda está ativa e é a mesma versão
        is_active = lambda: self.running and self._sim_id == sim_id
        acquired: list[str] = []

        for quadrant in ordered:
            # Tenta adquirir o portão deste quadrante (bloqueia até conseguir ou abortar)
            ok = self._quadrant_gates[quadrant].acquire(
                car_id, speed, arrival_time, is_active
            )
            if not ok:
                # Falhou (simulação encerrada): libera todos os quadrantes já adquiridos
                for q in reversed(acquired):
                    self._quadrant_gates[q].release(car_id)
                    with self._lock:
                        if self._quadrant_holders.get(q) == car_id:
                            self._quadrant_holders[q] = None
                return ()  # Sinaliza falha na aquisição
            acquired.append(quadrant)
            # Registra este veículo como ocupante do quadrante recém-adquirido
            with self._lock:
                self._quadrant_holders[quadrant] = car_id

        return quadrants  # Ambos os quadrantes adquiridos com sucesso

    def _release_quadrants(self, car_id: int, quadrants: tuple[str, ...]) -> None:
        # Remove este veículo como ocupante de todos os quadrantes informados
        with self._lock:
            for quadrant in quadrants:
                if self._quadrant_holders.get(quadrant) == car_id:
                    self._quadrant_holders[quadrant] = None

        # Libera os portões em ordem inversa (simetria com a aquisição em ordem crescente)
        for quadrant in sorted(
            quadrants,
            key=QUADRANT_INDEX.__getitem__,
            reverse=True,
        ):
            self._quadrant_gates[quadrant].release(car_id)

    def _release_quadrant(self, car_id: int, quadrant: str) -> None:
        # Remove este veículo como ocupante de um único quadrante
        with self._lock:
            if self._quadrant_holders.get(quadrant) == car_id:
                self._quadrant_holders[quadrant] = None
        # Libera o portão para que o próximo da fila possa entrar
        self._quadrant_gates[quadrant].release(car_id)

    # ── Geração de veículos ───────────────────────────────────────────────────

    def _generate_vehicle_specs(
        self,
    ) -> list[tuple[Direction, float, VehicleType, float, float]]:
        # Retorna sempre as mesmas especificações fixas para que todas as simulações
        # partam das mesmas condições — velocidade, faixa e posição inicial iguais.
        # Isso permite comparar FCFS, SJF e colisão com variáveis idênticas.
        return list(FIXED_VEHICLE_SPECS)

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _start_waiting(self, car: Car) -> None:
        # Coloca o veículo no estado de espera e registra o momento em que começou a esperar
        car.state = CarState.WAITING
        if car.waiting_since == 0.0:
            car.waiting_since = time.time()

    def _stop_waiting(self, car: Car) -> None:
        # Acumula o tempo que o veículo ficou esperando e reseta o marcador de início de espera
        if car.waiting_since > 0.0:
            car.total_wait_time += time.time() - car.waiting_since
            car.waiting_since = 0.0





#TEMPO
    def _finish_car(self, car_id: int, lbl: str) -> None:
        # Recupera o veículo; ignora se já foi removido
        car = self.cars.get(car_id)
        if car is None:
            return
        self._stop_waiting(car)  # Garante que o tempo de espera pendente seja acumulado

        # Calcula o tempo total de travessia desde o spawn até a saída do canvas
        final_time = time.time() - car.crossing_start if car.crossing_start > 0 else 0.0
        car.last_crossing_time = final_time
        car.final_time = final_time
        car.crossings = 1              # Marca que completou uma travessia
        car.state = CarState.FINISHED  # Atualiza estado para finalizado
        car.quadrant = ""              # Remove associação com quadrante

        # Incrementa o contador global de travessias concluídas (thread-safe)
        with self._lock:
            self._total_crossings += 1

        self._log(
            "finished",
            car_id,
            f"{lbl} concluiu em {car.last_crossing_time:.2f}s",
        )
        # Verifica se todos os veículos terminaram para encerrar a simulação
        self._maybe_finish_simulation()

    def _check_collision(self, current_q: str) -> None:
        # Conjunto de direções conflitantes para este quadrante
        valid_dirs = QUADRANT_DIRS[current_q]

        with self._collision_lock:
            # Coleta todos os veículos na região crítica dentro deste quadrante com direções conflitantes
            affected_ids = [
                cid for cid, car in self.cars.items()
                if car.state == CarState.IN_CRITICAL
                and car.direction in valid_dirs
                and _which_quadrant(car.x, car.y) == current_q
            ]

            if len(affected_ids) < 2:
                return  # Menos de 2 veículos — não há colisão possível

            dirs_present = {self.cars[cid].direction for cid in affected_ids}
            if len(dirs_present) < 2:
                return  # Todos na mesma direção — não colidem entre si

            # Filtra apenas veículos que ainda não foram registrados como colididos
            fresh_ids = [cid for cid in affected_ids if cid not in self._collided_set]
            if not fresh_ids:
                return  # Todos já foram processados nesta colisão

            collision_time = time.time()
            for cid in affected_ids:
                self._collided_set.add(cid)  # Marca como colidido para não processar novamente
                car = self.cars.get(cid)
                if car is None or car.state != CarState.IN_CRITICAL:
                    continue
                # Atualiza o estado e tempo final do veículo colidido
                car.state = CarState.COLLIDED
                car.final_time = (
                    collision_time - car.crossing_start
                    if car.crossing_start > 0
                    else 0.0
                )
                car.quadrant = current_q  # Registra o quadrante onde ocorreu a colisão
                self._stop_waiting(car)   # Garante acumulação de tempo de espera

            # Incrementa o contador global de colisões (thread-safe)
            with self._lock:
                self.stats.total_collisions += 1

            # Formata os IDs dos veículos envolvidos para o log
            names = " x ".join(str(cid) for cid in sorted(affected_ids))
            self._log("collision", None, f"Colisao em {current_q}: {names}")

        # Verifica se a colisão encerrou a simulação (todos os veículos finalizados ou colididos)
        self._maybe_finish_simulation()

    def _maybe_finish_simulation(self) -> None:
        with self._lock:
            if not self.running or not self.cars:
                return  # Simulação já encerrada ou sem veículos

            if not all(
                car.state in (CarState.FINISHED, CarState.COLLIDED)
                for car in self.cars.values()
            ):
                return  # Ainda há veículos em andamento

            # Todos os veículos terminaram — encerra a simulação
            self.running = False
            collision_count = self.stats.total_collisions

        if collision_count > 0:
            # Encerrada com colisões: informa a quantidade no log
            self._log(
                "complete",
                None,
                f"Simulacao encerrada com {collision_count} colisao(oes)",
            )
            return

        # Encerrada sem colisões: todas as travessias foram concluídas com sucesso
        self._log("complete", None, "Todas as travessias foram concluidas")

    def _log(self, etype: str, car_id: Optional[int], msg: str) -> None:
        # Calcula o tempo decorrido desde o início da simulação
        elapsed = round(time.time() - self._sim_start, 2)
        with self._events_lock:
            # Adiciona o evento à lista de forma thread-safe
            self.events.append(
                {
                    "time": elapsed,     # Tempo relativo ao início da simulação
                    "type": etype,       # Tipo do evento (spawn, enter, exit, collision, etc.)
                    "car_id": car_id,    # ID do veículo envolvido (None para eventos globais)
                    "message": msg,      # Descrição legível do evento
                }
            )
            if len(self.events) > MAX_EVENTS:
                # Mantém apenas os MAX_EVENTS eventos mais recentes para evitar crescimento ilimitado
                self.events = self.events[-MAX_EVENTS:]


# Instância para index.html (sync/colisão)
simulation_service = SimulationService()
# Instância para index2.html (FCFS vs SJF) — estado completamente isolado
simulation_service_2 = SimulationService()
