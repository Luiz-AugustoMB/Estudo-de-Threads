import threading
import time
import random

from models.car import Car, CarState, Direction
from models.simulation import SimulationStats

# ── Canvas ────────────────────────────────────────────────────────────────────
CANVAS_W = 500
CANVAS_H = 500

# ── Região crítica: 4 quadrantes do cruzamento ───────────────────────────────
#
#   Geometria (centro = 250,250):
#
#       x  190      250      310
#   y        |       |       |
#  190 ──────+───────────────+──
#            |  Q1   |  Q2   |
#            |  N×W  |  S×W  |
#  250 ──────+───────+───────+──
#            |  Q3   |  Q4   |
#            |  N×E  |  S×E  |
#  310 ──────+───────────────+──
#
#   Rota NORTH (x=220): Q1 (y∈[190,250]) → Q3 (y∈[250,310])
#   Rota SOUTH (x=280): Q4 (y∈[250,310]) → Q2 (y∈[190,250])
#   Rota WEST  (y=220): Q1 (x∈[190,250]) → Q2 (x∈[250,310])
#   Rota EAST  (y=280): Q4 (x∈[250,310]) → Q3 (x∈[190,250])
#
CRIT_X1, CRIT_X2 = 190, 310   # limites externos (usados no frontend)
CRIT_Y1, CRIT_Y2 = 190, 310
CRIT_CX, CRIT_CY = 250, 250   # centro — divisor dos quadrantes

# Direções que se cruzam fisicamente em cada quadrante
QUADRANT_DIRS: dict[str, set] = {
    "Q1": {Direction.NORTH, Direction.WEST},
    "Q2": {Direction.SOUTH, Direction.WEST},
    "Q3": {Direction.NORTH, Direction.EAST},
    "Q4": {Direction.SOUTH, Direction.EAST},
}

# ── Parâmetros de simulação ───────────────────────────────────────────────────
# STEP_DELAY é dinâmico — controlado pelo slider de velocidade em tempo real.
# Fórmula: delay = 0.15 / level  (level 1=lento … 12=rápido)
#   level=1  → 0.150s/passo (~7 fps)
#   level=4  → 0.037s/passo (~27 fps)  ← padrão
#   level=12 → 0.012s/passo (~80 fps)
DEFAULT_SPEED_LEVEL = 4
MAX_EVENTS = 100     # janela deslizante do log

# ── Rotas: 4 pistas separadas (x_ini, y_ini, unit_dx, unit_dy) ───────────────
# Pista esquerda da via vertical  → NORTH desce  em x=220
# Pista direita da via vertical   → SOUTH sobe   em x=280
# Pista superior da via horizontal→ WEST vai →   em y=220
# Pista inferior da via horizontal→ EAST vai ←   em y=280
ROUTES: dict[Direction, tuple[float, float, float, float]] = {
    Direction.NORTH: (220.0,  -20.0,  0.0,  1.0),
    Direction.SOUTH: (280.0,  520.0,  0.0, -1.0),
    Direction.WEST:  (-20.0,  220.0,  1.0,  0.0),
    Direction.EAST:  (520.0,  280.0, -1.0,  0.0),
}

DIR_LABEL = {
    Direction.NORTH: "↓", Direction.SOUTH: "↑",
    Direction.WEST:  "→", Direction.EAST:  "←",
}

def _which_quadrant(x: float, y: float) -> str | None:
    """Retorna o quadrante ("Q1"–"Q4") em que (x,y) está, ou None se fora."""
    if not (CRIT_X1 <= x <= CRIT_X2 and CRIT_Y1 <= y <= CRIT_Y2):
        return None
    left = x <= CRIT_CX
    top  = y <= CRIT_CY
    if   left and top:     return "Q1"
    elif not left and top: return "Q2"
    elif left:             return "Q3"
    else:                  return "Q4"


def _out_of_bounds(x: float, y: float) -> bool:
    return x < -50 or x > CANVAS_W + 50 or y < -50 or y > CANVAS_H + 50


class SimulationService:
    def __init__(self) -> None:
        self.cars: dict[str, Car] = {}
        self.stats = SimulationStats()
        self.running = False
        self._sim_id = 0
        self._sim_start_time = 0.0
        self.events: list[dict] = []
        self._stats_lock     = threading.Lock()
        self._collision_lock = threading.Lock()
        self._events_lock    = threading.Lock()
        self._collided_set: set[str] = set()
        self._step_delay: float = round(0.15 / DEFAULT_SPEED_LEVEL, 4)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_speed(self, level: int) -> None:
        """Atualiza o delay entre passos em tempo real (nível 1–12)."""
        self._step_delay = round(0.15 / level, 4)

    def start(self, num_cars: int, max_delay: float = 3.5) -> None:
        self._sim_id += 1
        sim_id = self._sim_id
        self._sim_start_time = time.time()

        self.cars = {}
        self.stats = SimulationStats(total_cars=num_cars, active_cars=num_cars)
        self.running = True
        self._collided_set = set()
        self.events = []

        directions = list(Direction)   # [NORTH, SOUTH, WEST, EAST]
        launches: list[tuple] = []

        for i in range(num_cars):
            direction = directions[i % 4]
            car_id    = f"car_{i + 1}"
            sx, sy, udx, udy = ROUTES[direction]

            # ── Velocidade individual por thread (aleatória por carro) ──────────
            # Cada thread nasce com velocidade própria (px/passo), independente
            # do slider — que controla apenas o ritmo global da simulação.
            individual_speed = random.uniform(3.0, 6.0)
            dx = udx * individual_speed
            dy = udy * individual_speed

            self.cars[car_id] = Car(id=car_id, direction=direction, x=sx, y=sy,
                                    speed=individual_speed)

            # Delay aleatório independente por thread
            delay = random.uniform(0.0, max_delay)
            launches.append((car_id, dx, dy, delay, sim_id))
            self._add_event(
                "start",
                f"{car_id} criada [{DIR_LABEL[direction]}] spd={individual_speed:.1f} delay={delay:.2f}s"
            )

        for args in launches:
            threading.Thread(target=self._car_thread, args=args, daemon=True).start()

    def reset(self) -> None:
        self._sim_id += 1
        self.cars = {}
        self.stats = SimulationStats()
        self.running = False
        self._collided_set = set()
        self.events = []

    def get_state(self) -> dict:
        with self._events_lock:
            events_snapshot = list(self.events)
        return {
            "running": self.running,
            "cars": [c.to_dict() for c in list(self.cars.values())],
            "stats": {
                "total":      self.stats.total_cars,
                "active":     self.stats.active_cars,
                "finished":   self.stats.finished_cars,
                "collisions": self.stats.collisions,
            },
            "events": events_snapshot,
        }

    # ── Thread de cada carro ──────────────────────────────────────────────────

    def _car_thread(self, car_id: str, dx: float, dy: float,
                    delay: float, sim_id: int) -> None:
        time.sleep(delay)

        crit_entry_time: float | None = None

        while True:
            if self._sim_id != sim_id:
                return

            car = self.cars.get(car_id)
            if car is None or car.state == CarState.FINISHED:
                return

            # ── MOVER — sem lock (race condition intencional) ─────────────────
            car.x += dx
            car.y += dy

            # ── REGIÃO CRÍTICA (por quadrante) ───────────────────────────────
            current_q = _which_quadrant(car.x, car.y)

            if current_q is not None:
                if car.state == CarState.MOVING:
                    # Primeira entrada na zona crítica
                    car.state = CarState.IN_CRITICAL
                    car.quadrant = current_q
                    crit_entry_time = time.time()
                    self._add_event("enter", f"{car_id} entrou [{current_q}]")
                elif car.state == CarState.IN_CRITICAL:
                    # Atualiza quadrante ao transitar (ex: Q1→Q3 para NORTH)
                    car.quadrant = current_q

                if crit_entry_time is not None:
                    car.time_in_critical = time.time() - crit_entry_time

                self._check_collision(current_q)

                # Thread para ao colidir — carro fica congelado com 💥
                if car.state == CarState.COLLIDED:
                    with self._stats_lock:
                        self.stats.active_cars = max(0, self.stats.active_cars - 1)
                    self._add_event("stop", f"{car_id} parou [{car.quadrant}]")
                    return

            else:
                if car.state == CarState.IN_CRITICAL:
                    car.state = CarState.MOVING
                    car.quadrant = ""
                    car.time_in_critical = 0.0
                    crit_entry_time = None
                    self._add_event("exit", f"{car_id} saiu sem colisão ✓")

            # ── LIMITES ───────────────────────────────────────────────────────
            if _out_of_bounds(car.x, car.y):
                car.state = CarState.FINISHED
                car.time_in_critical = 0.0
                with self._stats_lock:
                    self.stats.active_cars = max(0, self.stats.active_cars - 1)
                    self.stats.finished_cars += 1
                self._add_event("finish", f"{car_id} concluiu a rota")
                return

            time.sleep(self._step_delay)

    # ── Detecção de colisão por sub-região ───────────────────────────────────
    #
    # REGRA: colisão ocorre quando 2+ carros de direções distintas estão
    # simultaneamente no MESMO QUADRANTE (Q1–Q4).
    #
    # Cada quadrante tem exatamente 2 direções conflitantes (QUADRANT_DIRS).
    # Dois carros da mesma direção não colidem — estão em pistas paralelas.
    # Isso elimina falsos positivos que o modelo global gerava.

    def _check_collision(self, current_q: str) -> None:
        valid_dirs = QUADRANT_DIRS[current_q]

        # Snapshot sem lock — leitura concorrente intencional
        snapshot = list(self.cars.items())

        # Carros IN_CRITICAL dentro do mesmo quadrante e com direção válida.
        # COLIDIDOS e congelados são excluídos para evitar efeito cascata.
        in_same_q = [
            cid for cid, c in snapshot
            if c.state == CarState.IN_CRITICAL
            and c.direction in valid_dirs
            and _which_quadrant(c.x, c.y) == current_q
        ]

        if len(in_same_q) < 2:
            return

        # Exige ao menos 2 direções distintas — dois NORTH no mesmo quadrante
        # não representam race condition real.
        dirs_present = {self.cars[cid].direction for cid in in_same_q
                        if cid in self.cars}
        if len(dirs_present) < 2:
            return

        with self._collision_lock:
            fresh = [cid for cid in in_same_q if cid not in self._collided_set]
            if not fresh:
                return

            for cid in in_same_q:
                if cid not in self._collided_set:
                    self._collided_set.add(cid)
                    c = self.cars.get(cid)
                    if c and c.state == CarState.IN_CRITICAL:
                        c.state = CarState.COLLIDED

            with self._stats_lock:
                self.stats.collisions += 1

            names = " × ".join(in_same_q)
            self._add_event("collision", f"COLISAO [{current_q}]: {names}")

    # ── Utilitário interno ────────────────────────────────────────────────────

    def _add_event(self, event_type: str, message: str) -> None:
        elapsed = round(time.time() - self._sim_start_time, 2)
        with self._events_lock:
            self.events.append({"time": elapsed, "type": event_type, "message": message})
            if len(self.events) > MAX_EVENTS:
                self.events = self.events[-MAX_EVENTS:]


# Instância global compartilhada pelas rotas e WebSocket
simulation_service = SimulationService()
