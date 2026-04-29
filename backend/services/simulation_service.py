import heapq
import random
import threading
import time
from typing import Optional

from models.car import Car, CarState, Direction, VehicleType
from models.simulation import SimulationStats

CANVAS_W = 500
CANVAS_H = 500

CRIT_X1, CRIT_X2 = 190, 310
CRIT_Y1, CRIT_Y2 = 190, 310
CRIT_CX, CRIT_CY = 250, 250

LANE_NW_A = 216
LANE_NW_B = 224
LANE_SE_A = 276
LANE_SE_B = 284

STEP_DELAY = 0.04
MAX_EVENTS = 200
TOTAL_VEHICLES = 8
MIN_TRUCKS = 1
MAX_TRUCKS = 4
CAR_SPEED_RANGE = (4.0, 9.5)
TRUCK_SPEED_RANGE = (2.0, 5.5)
BASE_STAGGER_RANGE = (0.0, 60.0)
STAGGER_GAP = 140.0
STAGGER_VARIATION = 35.0

# Comprimento da travessia na região crítica (px) – usado pelo SJF
INTERSECTION_SIZE = float(CRIT_X2 - CRIT_X1)  # 120 px

LANES_BY_DIRECTION: dict[Direction, tuple[float, ...]] = {
    Direction.NORTH: (float(LANE_NW_A), float(LANE_NW_B)),
    Direction.SOUTH: (float(LANE_SE_A), float(LANE_SE_B)),
    Direction.WEST: (float(LANE_NW_A), float(LANE_NW_B)),
    Direction.EAST: (float(LANE_SE_A), float(LANE_SE_B)),
}

VEHICLE_LABEL = {VehicleType.CAR: "Carro", VehicleType.TRUCK: "Caminhao"}
DIR_LABEL = {
    Direction.NORTH: "topo->base",
    Direction.SOUTH: "base->topo",
    Direction.WEST: "esq->dir",
    Direction.EAST: "dir->esq",
}

PATH_QUADRANTS: dict[Direction, tuple[str, str]] = {
    Direction.NORTH: ("Q1", "Q3"),
    Direction.SOUTH: ("Q4", "Q2"),
    Direction.WEST: ("Q1", "Q2"),
    Direction.EAST: ("Q4", "Q3"),
}

QUADRANT_DIRS: dict[str, set[Direction]] = {
    "Q1": {Direction.NORTH, Direction.WEST},
    "Q2": {Direction.SOUTH, Direction.WEST},
    "Q3": {Direction.NORTH, Direction.EAST},
    "Q4": {Direction.SOUTH, Direction.EAST},
}

QUADRANT_NAMES = ("Q1", "Q2", "Q3", "Q4")
QUADRANT_INDEX = {name: idx for idx, name in enumerate(QUADRANT_NAMES)}


def _build_start_pos(
    direction: Direction,
    lane_coord: float,
    stagger: float,
) -> tuple[float, float]:
    if direction == Direction.NORTH:
        return (lane_coord, -stagger)
    if direction == Direction.SOUTH:
        return (lane_coord, CANVAS_H + stagger)
    if direction == Direction.WEST:
        return (-stagger, lane_coord)
    return (CANVAS_W + stagger, lane_coord)


def _direction_delta(direction: Direction) -> tuple[float, float]:
    return {
        Direction.NORTH: (0.0, 1.0),
        Direction.SOUTH: (0.0, -1.0),
        Direction.WEST: (1.0, 0.0),
        Direction.EAST: (-1.0, 0.0),
    }[direction]


def _in_critical(x: float, y: float) -> bool:
    return CRIT_X1 <= x <= CRIT_X2 and CRIT_Y1 <= y <= CRIT_Y2


def _next_in_critical(
    x: float,
    y: float,
    dx: float,
    dy: float,
    speed: float,
) -> bool:
    return _in_critical(x + dx * speed, y + dy * speed)


def _has_exited(car: Car) -> bool:
    if car.direction == Direction.NORTH:
        return car.y > CRIT_Y2
    if car.direction == Direction.SOUTH:
        return car.y < CRIT_Y1
    if car.direction == Direction.WEST:
        return car.x > CRIT_X2
    return car.x < CRIT_X1


def _out_of_bounds(car: Car) -> bool:
    if car.direction == Direction.NORTH:
        return car.y > CANVAS_H + 60
    if car.direction == Direction.SOUTH:
        return car.y < -60
    if car.direction == Direction.WEST:
        return car.x > CANVAS_W + 60
    return car.x < -60


def _which_quadrant(x: float, y: float) -> str:
    if not _in_critical(x, y):
        return ""

    left = x <= CRIT_CX
    top = y <= CRIT_CY
    if left and top:
        return "Q1"
    if not left and top:
        return "Q2"
    if left:
        return "Q3"
    return "Q4"


# ── Escalonador de quadrante ──────────────────────────────────────────────────

class QuadrantScheduler:
    """Portão de ocupação única com fila de prioridade.

    FCFS – atende na ordem de chegada à espera.
    SJF  – atende primeiro quem tem menor tempo de travessia (INTERSECTION_SIZE / speed).
    """

    def __init__(self, mode: str) -> None:
        self._mode = mode
        self._cv = threading.Condition()
        self._holder: Optional[int] = None
        self._waiters: list[tuple] = []
        self._seq = 0

    @property
    def holder(self) -> Optional[int]:
        return self._holder

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
            self._seq += 1
            seq = self._seq
            if self._mode == "fcfs":
                key = (arrival_time, seq)
            else:  # sjf
                job_time = INTERSECTION_SIZE / speed  # passos para cruzar
                key = (job_time, arrival_time, seq)

            heapq.heappush(self._waiters, (key, car_id))

            while True:
                if not is_active():
                    self._waiters = [(k, c) for k, c in self._waiters if c != car_id]
                    heapq.heapify(self._waiters)
                    self._cv.notify_all()
                    return False

                if (
                    self._holder is None
                    and self._waiters
                    and self._waiters[0][1] == car_id
                ):
                    heapq.heappop(self._waiters)
                    self._holder = car_id
                    return True

                self._cv.wait(timeout=0.05)

    def release(self, car_id: int) -> None:
        with self._cv:
            if self._holder == car_id:
                self._holder = None
            self._cv.notify_all()

    def wake_all(self) -> None:
        """Acorda todos os esperadores para que verifiquem is_active() e abortem."""
        with self._cv:
            self._cv.notify_all()


# ── Serviço de simulação ──────────────────────────────────────────────────────

class SimulationService:
    def __init__(self) -> None:
        self.cars: dict[int, Car] = {}
        self.stats = SimulationStats()
        self.running = False
        self.sync_enabled = True
        self._scheduling_mode = "fcfs"

        self._sim_id = 0
        self._sim_start = 0.0
        self._quadrant_gates: dict[str, QuadrantScheduler] = {}
        self._quadrant_holders: dict[str, Optional[int]] = {}
        self._collided_set: set[int] = set()
        self._total_crossings = 0
        self._lock = threading.Lock()
        self._collision_lock = threading.Lock()
        self._events_lock = threading.Lock()
        self.events: list[dict] = []
        self._reset_quadrant_control()

    # ── API pública ───────────────────────────────────────────────────────────

    def start(self, sync_enabled: bool = True, scheduling_mode: str = "fcfs") -> None:
        if self.running:
            self.reset()
            time.sleep(0.15)

        self._sim_id += 1
        sim_id = self._sim_id
        self.sync_enabled = sync_enabled
        self._scheduling_mode = scheduling_mode
        self._sim_start = time.time()
        self.running = True
        self._reset_quadrant_control()
        self._collided_set = set()
        self._total_crossings = 0
        self.events = []
        self.cars = {}

        generated_vehicles = self._generate_vehicle_specs()
        now = time.time()
        for i, (direction, speed, vtype, lane_coord, stagger) in enumerate(generated_vehicles):
            sx, sy = _build_start_pos(direction, float(lane_coord), float(stagger))
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
            self._log(
                "spawn",
                i,
                (
                    f"{VEHICLE_LABEL[vtype]} {i} gerado em {DIR_LABEL[direction]} | "
                    f"pista={lane_coord:.0f} | vel={speed:.1f} | atraso={stagger:.0f}px"
                ),
            )

        mode_text = (
            f"semaforos ON - escalonamento {scheduling_mode.upper()}"
            if sync_enabled
            else "semaforos OFF - colisao livre"
        )
        self.stats = SimulationStats(total_vehicles=len(self.cars))
        self._log("start", None, f"Simulacao iniciada - frota aleatoria | {mode_text}")

        for car_id in self.cars:
            threading.Thread(
                target=self._vehicle_thread,
                args=(car_id, sim_id, sync_enabled),
                daemon=True,
            ).start()

    def reset(self) -> None:
        self._sim_id += 1
        self.running = False
        for gate in self._quadrant_gates.values():
            gate.wake_all()
        self.cars = {}
        self.stats = SimulationStats()
        self._total_crossings = 0
        self._collided_set = set()
        self._reset_quadrant_control()
        with self._events_lock:
            self.events = []

    def get_state(self) -> dict:
        with self._lock:
            crossings = self._total_crossings
            collisions = self.stats.total_collisions
            quadrants = {
                name: {"free": holder is None, "holder": holder}
                for name, holder in self._quadrant_holders.items()
            }

        with self._events_lock:
            events_snap = list(self.events)

        return {
            "running": self.running,
            "cars": [c.to_dict() for c in list(self.cars.values())],
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
        if sync_enabled:
            self._vehicle_thread_sync(car_id, sim_id)
            return
        self._vehicle_thread_collision(car_id, sim_id)

    def _vehicle_thread_sync(self, car_id: int, sim_id: int) -> None:
        car = self.cars.get(car_id)
        if car is None:
            return
        dx, dy = _direction_delta(car.direction)
        first_quadrant, second_quadrant = PATH_QUADRANTS[car.direction]
        held_quadrants: list[str] = []
        lbl = f"{VEHICLE_LABEL[car.vehicle_type]} {car_id} ({DIR_LABEL[car.direction]})"

        while self.running and self._sim_id == sim_id:
            if not held_quadrants and _next_in_critical(car.x, car.y, dx, dy, car.speed):
                self._start_waiting(car)
                self._log(
                    "waiting",
                    car_id,
                    f"{lbl} aguardando {first_quadrant} + {second_quadrant}",
                )

                acquired_quadrants = self._acquire_quadrants(
                    car_id=car_id,
                    quadrants=(first_quadrant, second_quadrant),
                    speed=car.speed,
                    arrival_time=car.waiting_since,
                    sim_id=sim_id,
                )
                if not acquired_quadrants:
                    self._stop_waiting(car)
                    return

                held_quadrants = list(acquired_quadrants)
                self._stop_waiting(car)
                car.state = CarState.IN_CRITICAL
                self._log(
                    "enter",
                    car_id,
                    f"{lbl} reservou {first_quadrant} + {second_quadrant} e entrou",
                )

            car.x += dx * car.speed
            car.y += dy * car.speed

            if _in_critical(car.x, car.y):
                car.state = CarState.IN_CRITICAL
                car.quadrant = _which_quadrant(car.x, car.y)
            else:
                car.quadrant = ""
                if car.state == CarState.IN_CRITICAL:
                    car.state = CarState.MOVING

            if (
                len(held_quadrants) == 2
                and car.quadrant == second_quadrant
                and first_quadrant in held_quadrants
            ):
                self._release_quadrant(car_id, first_quadrant)
                held_quadrants.remove(first_quadrant)
                self._log(
                    "handoff",
                    car_id,
                    f"{lbl} liberou {first_quadrant} e manteve {second_quadrant}",
                )

            if held_quadrants and _has_exited(car):
                self._release_quadrants(car_id, tuple(held_quadrants))
                held_quadrants = []
                car.state = CarState.MOVING
                self._log("exit", car_id, f"{lbl} saiu e liberou o trajeto")

            if _out_of_bounds(car):
                if held_quadrants:
                    self._release_quadrants(car_id, tuple(held_quadrants))
                self._finish_car(car_id, lbl)
                return

            time.sleep(STEP_DELAY)

    def _vehicle_thread_collision(self, car_id: int, sim_id: int) -> None:
        car = self.cars.get(car_id)
        if car is None:
            return
        dx, dy = _direction_delta(car.direction)
        lbl = f"{VEHICLE_LABEL[car.vehicle_type]} {car_id} ({DIR_LABEL[car.direction]})"

        while self.running and self._sim_id == sim_id:
            if car.state == CarState.COLLIDED:
                return

            previous_quadrant = car.quadrant
            car.x += dx * car.speed
            car.y += dy * car.speed

            current_quadrant = _which_quadrant(car.x, car.y)
            if current_quadrant:
                if car.state != CarState.IN_CRITICAL:
                    car.state = CarState.IN_CRITICAL
                    car.quadrant = current_quadrant
                    self._log(
                        "enter",
                        car_id,
                        f"{lbl} entrou em {current_quadrant} sem sincronizacao",
                    )
                else:
                    car.quadrant = current_quadrant
                    if previous_quadrant and previous_quadrant != current_quadrant:
                        self._log(
                            "handoff",
                            car_id,
                            f"{lbl} avancou de {previous_quadrant} para {current_quadrant}",
                        )

                self._check_collision(current_quadrant)
                if car.state == CarState.COLLIDED:
                    return
            else:
                car.quadrant = ""
                if car.state == CarState.IN_CRITICAL:
                    car.state = CarState.MOVING
                    self._log("exit", car_id, f"{lbl} cruzou sem colisao")

            if _out_of_bounds(car):
                self._finish_car(car_id, lbl)
                return

            time.sleep(STEP_DELAY)

    # ── Controle de quadrantes ────────────────────────────────────────────────

    def _reset_quadrant_control(self) -> None:
        self._quadrant_gates = {
            name: QuadrantScheduler(self._scheduling_mode) for name in QUADRANT_NAMES
        }
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
        ordered = tuple(sorted(quadrants, key=QUADRANT_INDEX.__getitem__))
        is_active = lambda: self.running and self._sim_id == sim_id
        acquired: list[str] = []

        for quadrant in ordered:
            ok = self._quadrant_gates[quadrant].acquire(
                car_id, speed, arrival_time, is_active
            )
            if not ok:
                for q in reversed(acquired):
                    self._quadrant_gates[q].release(car_id)
                    with self._lock:
                        if self._quadrant_holders.get(q) == car_id:
                            self._quadrant_holders[q] = None
                return ()
            acquired.append(quadrant)
            with self._lock:
                self._quadrant_holders[quadrant] = car_id

        return quadrants

    def _release_quadrants(self, car_id: int, quadrants: tuple[str, ...]) -> None:
        with self._lock:
            for quadrant in quadrants:
                if self._quadrant_holders.get(quadrant) == car_id:
                    self._quadrant_holders[quadrant] = None

        for quadrant in sorted(
            quadrants,
            key=QUADRANT_INDEX.__getitem__,
            reverse=True,
        ):
            self._quadrant_gates[quadrant].release(car_id)

    def _release_quadrant(self, car_id: int, quadrant: str) -> None:
        with self._lock:
            if self._quadrant_holders.get(quadrant) == car_id:
                self._quadrant_holders[quadrant] = None

        self._quadrant_gates[quadrant].release(car_id)

    # ── Geração de veículos ───────────────────────────────────────────────────

    def _generate_vehicle_specs(
        self,
    ) -> list[tuple[Direction, float, VehicleType, float, float]]:
        directions = list(Direction)
        direction_pool = directions.copy()
        while len(direction_pool) < TOTAL_VEHICLES:
            direction_pool.append(random.choice(directions))
        random.shuffle(direction_pool)

        truck_count = random.randint(MIN_TRUCKS, min(MAX_TRUCKS, TOTAL_VEHICLES - 1))
        vehicle_types = (
            [VehicleType.TRUCK] * truck_count
            + [VehicleType.CAR] * (TOTAL_VEHICLES - truck_count)
        )
        random.shuffle(vehicle_types)

        lane_slots: dict[tuple[Direction, float], int] = {}
        specs: list[tuple[Direction, float, VehicleType, float, float]] = []

        for direction, vehicle_type in zip(direction_pool, vehicle_types):
            lane_coord = random.choice(LANES_BY_DIRECTION[direction])
            slot_key = (direction, lane_coord)
            slot_index = lane_slots.get(slot_key, 0)
            lane_slots[slot_key] = slot_index + 1

            speed_min, speed_max = (
                TRUCK_SPEED_RANGE if vehicle_type == VehicleType.TRUCK
                else CAR_SPEED_RANGE
            )
            speed = round(random.uniform(speed_min, speed_max), 1)
            stagger = round(
                random.uniform(*BASE_STAGGER_RANGE)
                + slot_index * (STAGGER_GAP + random.uniform(0.0, STAGGER_VARIATION)),
                1,
            )

            specs.append((direction, speed, vehicle_type, lane_coord, stagger))

        random.shuffle(specs)
        return specs

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _start_waiting(self, car: Car) -> None:
        car.state = CarState.WAITING
        if car.waiting_since == 0.0:
            car.waiting_since = time.time()

    def _stop_waiting(self, car: Car) -> None:
        if car.waiting_since > 0.0:
            car.total_wait_time += time.time() - car.waiting_since
            car.waiting_since = 0.0

    def _finish_car(self, car_id: int, lbl: str) -> None:
        car = self.cars.get(car_id)
        if car is None:
            return
        self._stop_waiting(car)

        final_time = time.time() - car.crossing_start if car.crossing_start > 0 else 0.0
        car.last_crossing_time = final_time
        car.final_time = final_time
        car.crossings = 1
        car.state = CarState.FINISHED
        car.quadrant = ""

        with self._lock:
            self._total_crossings += 1

        self._log(
            "finished",
            car_id,
            f"{lbl} concluiu em {car.last_crossing_time:.2f}s",
        )
        self._maybe_finish_simulation()

    def _check_collision(self, current_q: str) -> None:
        valid_dirs = QUADRANT_DIRS[current_q]

        with self._collision_lock:
            affected_ids = [
                cid for cid, car in self.cars.items()
                if car.state == CarState.IN_CRITICAL
                and car.direction in valid_dirs
                and _which_quadrant(car.x, car.y) == current_q
            ]

            if len(affected_ids) < 2:
                return

            dirs_present = {self.cars[cid].direction for cid in affected_ids}
            if len(dirs_present) < 2:
                return

            fresh_ids = [cid for cid in affected_ids if cid not in self._collided_set]
            if not fresh_ids:
                return

            collision_time = time.time()
            for cid in affected_ids:
                self._collided_set.add(cid)
                car = self.cars.get(cid)
                if car is None or car.state != CarState.IN_CRITICAL:
                    continue
                car.state = CarState.COLLIDED
                car.final_time = (
                    collision_time - car.crossing_start
                    if car.crossing_start > 0
                    else 0.0
                )
                car.quadrant = current_q
                self._stop_waiting(car)

            with self._lock:
                self.stats.total_collisions += 1

            names = " x ".join(str(cid) for cid in sorted(affected_ids))
            self._log("collision", None, f"Colisao em {current_q}: {names}")

        self._maybe_finish_simulation()

    def _maybe_finish_simulation(self) -> None:
        with self._lock:
            if not self.running or not self.cars:
                return

            if not all(
                car.state in (CarState.FINISHED, CarState.COLLIDED)
                for car in self.cars.values()
            ):
                return

            self.running = False
            collision_count = self.stats.total_collisions

        if collision_count > 0:
            self._log(
                "complete",
                None,
                f"Simulacao encerrada com {collision_count} colisao(oes)",
            )
            return

        self._log("complete", None, "Todas as travessias foram concluidas")

    def _log(self, etype: str, car_id: Optional[int], msg: str) -> None:
        elapsed = round(time.time() - self._sim_start, 2)
        with self._events_lock:
            self.events.append(
                {
                    "time": elapsed,
                    "type": etype,
                    "car_id": car_id,
                    "message": msg,
                }
            )
            if len(self.events) > MAX_EVENTS:
                self.events = self.events[-MAX_EVENTS:]


simulation_service = SimulationService()
