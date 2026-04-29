// ── Configuração do backend ───────────────────────────────────────────────────
const BACKEND_PORT = 8001;
const BACKEND_HTTP = `http://localhost:${BACKEND_PORT}`;
const BACKEND_WS   = `ws://localhost:${BACKEND_PORT}`;

// ── Elementos do DOM ──────────────────────────────────────────────────────────
const canvas       = document.getElementById('sim-canvas');
const ctx          = canvas.getContext('2d');
const elTotal      = document.getElementById('stat-total');
const elCrossings  = document.getElementById('stat-crossings');
const elStatus     = document.getElementById('status-msg');
const btnStart     = document.getElementById('btn-start');
const btnReset     = document.getElementById('btn-reset');
const btnClearLog  = document.getElementById('btn-clear-log');
const btnSchedFcfs = document.getElementById('btn-sched-fcfs');
const btnSchedSjf  = document.getElementById('btn-sched-sjf');
const elModeNote   = document.getElementById('mode-note');
const fcfsTbody    = document.getElementById('fcfs-tbody');
const sjfTbody     = document.getElementById('sjf-tbody');
const logList      = document.getElementById('log-list');

// ── Geometria ─────────────────────────────────────────────────────────────────
const W        = canvas.width;
const H        = canvas.height;
const CX       = W / 2;
const CY       = H / 2;
const ROAD_HALF = 60;
const CX1 = CX - ROAD_HALF;
const CX2 = CX + ROAD_HALF;
const CY1 = CY - ROAD_HALF;
const CY2 = CY + ROAD_HALF;

const LANE = { north: { x: 220 }, south: { x: 280 }, west: { y: 220 }, east: { y: 280 } };

// ── Dimensões e cores ─────────────────────────────────────────────────────────
const VEHICLE_SIZE = { car: { w: 12, h: 18 }, truck: { w: 17, h: 26 } };

const VEHICLE_NAME = { car: 'Carro', truck: 'Caminhao' };
const DIR_LABEL    = { north: 'N->S', south: 'S->N', west: 'W->E', east: 'E->W' };

const STATE_LABEL = {
  moving:      'movendo',
  waiting:     'aguardando',
  in_critical: 'cruzamento',
  finished:    'concluido',
};

const SCHED_DESC = {
  fcfs: 'FCFS: atende na ordem de chegada.',
  sjf:  'SJF: atende primeiro o menor job (mais rapido).',
};

const DEFAULT_QUADRANTS = {
  Q1: { free: true, holder: null },
  Q2: { free: true, holder: null },
  Q3: { free: true, holder: null },
  Q4: { free: true, holder: null },
};

const QUAD_META = [
  { name: 'Q1', label: 'N x W', x: CX1, y: CY1, w: CX - CX1, h: CY - CY1,
    fill: 'rgba(59,130,246,0.10)', stroke: 'rgba(59,130,246,0.50)' },
  { name: 'Q2', label: 'S x W', x: CX,  y: CY1, w: CX2 - CX, h: CY - CY1,
    fill: 'rgba(245,158,11,0.10)', stroke: 'rgba(245,158,11,0.50)' },
  { name: 'Q3', label: 'N x E', x: CX1, y: CY,  w: CX - CX1, h: CY2 - CY,
    fill: 'rgba(34,197,94,0.10)', stroke: 'rgba(34,197,94,0.50)' },
  { name: 'Q4', label: 'S x E', x: CX,  y: CY,  w: CX2 - CX, h: CY2 - CY,
    fill: 'rgba(168,85,247,0.10)', stroke: 'rgba(168,85,247,0.50)' },
];

// ── Estado global ─────────────────────────────────────────────────────────────
let simState = {
  running: false,
  cars: [],
  stats: {
    total_vehicles: 0,
    total_crossings: 0,
    mode: 'sync',
    sync_enabled: true,
    scheduling_mode: 'fcfs',
    quadrants: { ...DEFAULT_QUADRANTS },
  },
  events: [],
};

let lastEventCount  = 0;
let localLog        = [];
let selectedMode    = 'fcfs';  // modo selecionado para o próximo início
let prevRunning     = false;   // detecta fim de simulação

// Snapshots congelados para comparação
let fcfsSnapshot = [];
let sjfSnapshot  = [];

// ── Utilitários DOM ───────────────────────────────────────────────────────────
function setStatus(msg) { elStatus.textContent = msg; }

function getQuadrants() {
  return simState.stats?.quadrants ?? DEFAULT_QUADRANTS;
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  const ws = new WebSocket(`${BACKEND_WS}/ws`);

  ws.onmessage = (ev) => {
    const prev = prevRunning;
    simState = JSON.parse(ev.data);
    simState.stats = {
      total_vehicles:   simState.stats?.total_vehicles   ?? 0,
      total_crossings:  simState.stats?.total_crossings  ?? 0,
      mode:             simState.stats?.mode             ?? 'sync',
      sync_enabled:     simState.stats?.sync_enabled     ?? true,
      scheduling_mode:  simState.stats?.scheduling_mode  ?? 'fcfs',
      quadrants: { ...DEFAULT_QUADRANTS, ...(simState.stats?.quadrants ?? {}) },
    };
    prevRunning = simState.running;

    const mode = simState.stats.scheduling_mode;

    if (simState.running) {
      // Atualiza ao vivo apenas a tabela do modo ativo
      renderTableBody(mode === 'fcfs' ? fcfsTbody : sjfTbody, simState.cars);
    } else if (prev && !simState.running && simState.cars.length > 0) {
      // Simulação acabou de terminar: congela snapshot e troca sugestão de modo
      if (mode === 'fcfs') {
        fcfsSnapshot = [...simState.cars];
        renderTableBody(fcfsTbody, fcfsSnapshot);
      } else {
        sjfSnapshot = [...simState.cars];
        renderTableBody(sjfTbody, sjfSnapshot);
      }
      // Sugere rodar o outro modo
      selectedMode = mode === 'fcfs' ? 'sjf' : 'fcfs';
      refreshSchedButtons();
    }

    refreshStats();
    refreshStatus();

    if (simState.events.length !== lastEventCount) {
      lastEventCount = simState.events.length;
      localLog = [...simState.events];
      refreshLog();
    }
  };

  ws.onclose = () => setStatus('Conexao encerrada. Recarregue a pagina.');
  ws.onerror = () => setStatus(`Erro ao conectar na porta ${BACKEND_PORT}.`);
}

// ── Controles ─────────────────────────────────────────────────────────────────
btnStart.addEventListener('click', async () => {
  localLog = [];
  lastEventCount = 0;
  await fetch(`${BACKEND_HTTP}/api/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sync_enabled: true, scheduling_mode: selectedMode }),
  });
});

btnReset.addEventListener('click', async () => {
  await fetch(`${BACKEND_HTTP}/api/reset`, { method: 'POST' });
  localLog = [];
  lastEventCount = 0;
  logList.innerHTML = '<span class="log-empty">Nenhum evento ainda...</span>';
  // Tabelas mantêm os snapshots para comparação
});

btnSchedFcfs.addEventListener('click', () => {
  selectedMode = 'fcfs';
  refreshSchedButtons();
});

btnSchedSjf.addEventListener('click', () => {
  selectedMode = 'sjf';
  refreshSchedButtons();
});

btnClearLog.addEventListener('click', () => {
  localLog = [];
  logList.innerHTML = '<span class="log-empty">Log limpo.</span>';
});

// ── Botões de escalonamento ───────────────────────────────────────────────────
function refreshSchedButtons() {
  btnSchedFcfs.classList.toggle('active', selectedMode === 'fcfs');
  btnSchedSjf.classList.toggle('active',  selectedMode === 'sjf');
  elModeNote.textContent = SCHED_DESC[selectedMode];
}

// ── Estatísticas ──────────────────────────────────────────────────────────────
function refreshStats() {
  elTotal.textContent    = simState.stats.total_vehicles;
  elCrossings.textContent = simState.stats.total_crossings;
}

function refreshStatus() {
  const { running, stats } = simState;
  const mode = stats.scheduling_mode ?? 'fcfs';
  if (!running && stats.total_vehicles === 0) {
    setStatus(`Aguardando inicio... modo ${mode.toUpperCase()} selecionado.`);
  } else if (running) {
    setStatus(`Em andamento — escalonamento ${mode.toUpperCase()} ativo.`);
  } else {
    const allDone = simState.cars.length > 0
      && simState.cars.every((c) => c.state === 'finished');
    setStatus(
      allDone
        ? `Simulacao ${mode.toUpperCase()} concluida. Rode a outra para comparar.`
        : 'Simulacao pausada.',
    );
  }
}

// ── Tabelas de threads ────────────────────────────────────────────────────────
function renderTableBody(tbody, cars) {
  if (!cars || !cars.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Nenhuma simulacao</td></tr>`;
    return;
  }

  tbody.innerHTML = cars.map((car) => {
    const stateClass = car.state ? `ts-${car.state}` : 'ts-idle';
    const totalTime  = car.total_time != null ? `${car.total_time.toFixed(2)}s` : '-';
    const waitTime   = car.wait_time  != null ? `${car.wait_time.toFixed(2)}s`  : '-';

    return `
      <tr>
        <td>${car.id}</td>
        <td class="${car.vehicle_type === 'truck' ? 'type-truck' : 'type-car'}">
          ${VEHICLE_NAME[car.vehicle_type] ?? car.vehicle_type}
        </td>
        <td>${DIR_LABEL[car.direction] ?? car.direction}</td>
        <td class="speed-col">${car.speed}</td>
        <td class="time-col ${stateClass}">${totalTime}</td>
        <td class="time-col">${waitTime}</td>
      </tr>`;
  }).join('');
}

// ── Log de eventos ────────────────────────────────────────────────────────────
function refreshLog() {
  if (!localLog.length) {
    logList.innerHTML = '<span class="log-empty">Nenhum evento ainda...</span>';
    return;
  }
  logList.innerHTML = [...localLog].reverse()
    .map((ev) => (
      `<div class="log-entry log-${ev.type}">[${String(ev.time.toFixed(2)).padStart(6)}s] ${ev.message}</div>`
    ))
    .join('');
}

// ── Canvas: utilitários ───────────────────────────────────────────────────────
function rRect(x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) { ctx.roundRect(x, y, w, h, r); return; }
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);   ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);   ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);       ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// ── Canvas: pista ─────────────────────────────────────────────────────────────
function drawRoad() {
  ctx.fillStyle = '#091a3a';
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = '#374151';
  ctx.fillRect(CX - ROAD_HALF, 0, ROAD_HALF * 2, H);
  ctx.fillRect(0, CY - ROAD_HALF, W, ROAD_HALF * 2);

  ctx.save();
  ctx.strokeStyle = '#6b7280'; ctx.lineWidth = 1.5; ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(CX1, 0);   ctx.lineTo(CX1, CY1);
  ctx.moveTo(CX1, CY2); ctx.lineTo(CX1, H);
  ctx.moveTo(CX2, 0);   ctx.lineTo(CX2, CY1);
  ctx.moveTo(CX2, CY2); ctx.lineTo(CX2, H);
  ctx.moveTo(0, CY1);   ctx.lineTo(CX1, CY1);
  ctx.moveTo(CX2, CY1); ctx.lineTo(W, CY1);
  ctx.moveTo(0, CY2);   ctx.lineTo(CX1, CY2);
  ctx.moveTo(CX2, CY2); ctx.lineTo(W, CY2);
  ctx.stroke();

  ctx.strokeStyle = '#4b5563'; ctx.lineWidth = 1; ctx.setLineDash([8, 6]);
  ctx.beginPath();
  ctx.moveTo(CX, 0);   ctx.lineTo(CX, CY1);
  ctx.moveTo(CX, CY2); ctx.lineTo(CX, H);
  ctx.moveTo(0, CY);   ctx.lineTo(CX1, CY);
  ctx.moveTo(CX2, CY); ctx.lineTo(W, CY);
  ctx.stroke();
  ctx.restore();

  ctx.font = 'bold 13px sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = 'rgba(59,130,246,0.35)';
  [55, 115, H - 115, H - 55].forEach((y) => ctx.fillText('v', LANE.north.x, y));
  ctx.fillStyle = 'rgba(22,163,74,0.4)';
  [55, 115, H - 115, H - 55].forEach((y) => ctx.fillText('^', LANE.south.x, y));
  ctx.fillStyle = 'rgba(59,130,246,0.35)';
  [55, 115, W - 115, W - 55].forEach((x) => ctx.fillText('>', x, LANE.west.y));
  ctx.fillStyle = 'rgba(22,163,74,0.4)';
  [55, 115, W - 115, W - 55].forEach((x) => ctx.fillText('<', x, LANE.east.y));
}

// ── Canvas: região crítica e rótulo do modo ───────────────────────────────────
function drawCriticalRegion() {
  QUAD_META.forEach((q) => {
    ctx.fillStyle = q.fill;
    ctx.fillRect(q.x, q.y, q.w, q.h);
  });

  ctx.save();
  ctx.setLineDash([4, 3]); ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(CX, CY1); ctx.lineTo(CX, CY2);
  ctx.moveTo(CX1, CY); ctx.lineTo(CX2, CY);
  ctx.stroke();
  ctx.restore();

  ctx.save();
  ctx.setLineDash([6, 4]); ctx.strokeStyle = '#f97316'; ctx.lineWidth = 1.5;
  ctx.strokeRect(CX1 + 1, CY1 + 1, CX2 - CX1 - 2, CY2 - CY1 - 2);
  ctx.restore();

  ctx.font = 'bold 8px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  QUAD_META.forEach((q) => {
    ctx.fillStyle = q.stroke;
    ctx.fillText(q.name,  q.x + q.w / 2, q.y + q.h / 2 - 5);
    ctx.fillText(q.label, q.x + q.w / 2, q.y + q.h / 2 + 5);
  });

  // Rótulo do modo ativo no topo da região
  const mode = simState.stats?.scheduling_mode ?? 'fcfs';
  const modeColor = mode === 'fcfs' ? '#60a5fa' : '#4ade80';
  ctx.fillStyle = modeColor;
  ctx.font = 'bold 9px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(`REGIAO CRITICA — ${mode.toUpperCase()}`, (CX1 + CX2) / 2, CY1 - 5);
}

// ── Canvas: semáforos por quadrante ──────────────────────────────────────────
function drawQuadrantLight(tx, ty, label, occupied) {
  const tw = 16, th = 34;
  ctx.fillStyle = '#111827';
  rRect(tx, ty, tw, th, 3); ctx.fill();
  ctx.strokeStyle = '#374151'; ctx.lineWidth = 1;
  rRect(tx, ty, tw, th, 3); ctx.stroke();

  ctx.beginPath();
  ctx.arc(tx + tw / 2, ty + 10, 4, 0, Math.PI * 2);
  ctx.fillStyle = occupied ? '#7f1d1d' : '#1f2937'; ctx.fill();

  ctx.beginPath();
  ctx.arc(tx + tw / 2, ty + 24, 4, 0, Math.PI * 2);
  ctx.fillStyle = occupied ? '#f97316' : '#22c55e'; ctx.fill();

  ctx.fillStyle = 'rgba(255,255,255,0.38)'; ctx.font = '6px monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(label, tx + tw / 2, ty + th + 8);
}

function drawTrafficLights() {
  const quadrants = getQuadrants();
  drawQuadrantLight(CX1 - 24, CY1 - 2,  'Q1', !(quadrants.Q1?.free ?? true));
  drawQuadrantLight(CX2 +  8, CY1 - 2,  'Q2', !(quadrants.Q2?.free ?? true));
  drawQuadrantLight(CX1 - 24, CY2 - 32, 'Q3', !(quadrants.Q3?.free ?? true));
  drawQuadrantLight(CX2 +  8, CY2 - 32, 'Q4', !(quadrants.Q4?.free ?? true));
}

// ── Canvas: veículo ───────────────────────────────────────────────────────────
function vehicleColor(car) {
  if (car.state === 'waiting')     return '#f59e0b';
  if (car.state === 'in_critical') return '#f97316';
  if (car.state === 'finished')    return '#374151';
  return car.vehicle_type === 'truck' ? '#16a34a' : '#3b82f6';
}

function drawVehicle(car) {
  if (car.state === 'finished') return;

  const vertical = car.direction === 'north' || car.direction === 'south';
  const size = VEHICLE_SIZE[car.vehicle_type] ?? VEHICLE_SIZE.car;
  const cw = vertical ? size.w : size.h;
  const ch = vertical ? size.h : size.w;
  const x  = car.x - cw / 2;
  const y  = car.y - ch / 2;

  ctx.fillStyle = 'rgba(0,0,0,0.4)';
  rRect(x + 2, y + 2, cw, ch, 3); ctx.fill();

  ctx.fillStyle = vehicleColor(car);
  rRect(x, y, cw, ch, 3); ctx.fill();

  ctx.fillStyle = 'rgba(255,255,255,0.2)';
  if (vertical) ctx.fillRect(x + 2, y + 2, cw - 4, ch * 0.35);
  else          ctx.fillRect(x + 2, y + 2, cw * 0.35, ch - 4);

  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.font = `bold ${car.vehicle_type === 'truck' ? 8 : 7}px monospace`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(car.id, car.x, car.y + 2);

  if (car.state === 'waiting') {
    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 1.5;
    rRect(x - 1, y - 1, cw + 2, ch + 2, 4); ctx.stroke();
  }
}

// ── Loop de renderização ──────────────────────────────────────────────────────
function render() {
  drawRoad();
  drawCriticalRegion();
  drawTrafficLights();
  simState.cars.forEach(drawVehicle);
  requestAnimationFrame(render);
}

// ── Inicialização ─────────────────────────────────────────────────────────────
refreshSchedButtons();
connect();
render();
