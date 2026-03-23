// ── Configuração do backend ───────────────────────────────────────────────────
const BACKEND_PORT = 8001;
const BACKEND_HTTP = `http://localhost:${BACKEND_PORT}`;
const BACKEND_WS   = `ws://localhost:${BACKEND_PORT}`;

// ── Elementos do DOM ──────────────────────────────────────────────────────────
const canvas       = document.getElementById('sim-canvas');
const ctx          = canvas.getContext('2d');
const elTotal      = document.getElementById('stat-total');
const elActive     = document.getElementById('stat-active');
const elFinished   = document.getElementById('stat-finished');
const elCollisions = document.getElementById('stat-collisions');
const elStatus     = document.getElementById('status-msg');
const btnStart     = document.getElementById('btn-start');
const btnReset     = document.getElementById('btn-reset');
const btnClearLog  = document.getElementById('btn-clear-log');
const inputCars    = document.getElementById('num-cars');
const sliderSpeed  = document.getElementById('slider-speed');
const sliderDelay  = document.getElementById('slider-delay');
const elDelayVal   = document.getElementById('delay-val');
const elSpeedVal   = document.getElementById('speed-val');
const threadTbody  = document.getElementById('thread-tbody');
const logList      = document.getElementById('log-list');

// ── Layout (deve coincidir com backend) ───────────────────────────────────────
const W = canvas.width;    // 500
const H = canvas.height;   // 500
const CX = W / 2;          // 250
const CY = H / 2;          // 250
const ROAD_HALF = 60;      // meia-largura total da via → via = 120px

// Borda da região crítica (= borda da via)
const CX1 = CX - ROAD_HALF;  // 190
const CX2 = CX + ROAD_HALF;  // 310
const CY1 = CY - ROAD_HALF;  // 190
const CY2 = CY + ROAD_HALF;  // 310

// Centros das 4 pistas (devem coincidir com ROUTES no backend)
const LANE = {
  north: { x: 220 },   // pista esquerda da via vertical  (desce)
  south: { x: 280 },   // pista direita da via vertical   (sobe)
  west:  { y: 220 },   // pista superior da via horizontal (vai →)
  east:  { y: 280 },   // pista inferior da via horizontal (vai ←)
};

// ── Cores por estado ──────────────────────────────────────────────────────────
const COLORS = {
  moving:      '#3b82f6',
  in_critical: '#f59e0b',
  collided:    '#ef4444',
  finished:    '#22c55e',
};

// ── Estado global ─────────────────────────────────────────────────────────────
let simState = {
  running: false,
  cars: [],
  stats: { total: 0, active: 0, finished: 0, collisions: 0 },
  events: [],
};
let lastEventCount = 0;
let localLog = [];

// ── Sliders ───────────────────────────────────────────────────────────────────
sliderSpeed.addEventListener('input', () => {
  const level = parseInt(sliderSpeed.value);
  elSpeedVal.textContent = level;
  // Atualiza velocidade da simulação em tempo real, mesmo durante execução
  fetch(`${BACKEND_HTTP}/api/speed`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ level }),
  });
});
sliderDelay.addEventListener('input', () => {
  elDelayVal.textContent = parseFloat(sliderDelay.value).toFixed(1);
});

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  const ws = new WebSocket(`${BACKEND_WS}/ws`);

  ws.onmessage = (ev) => {
    simState = JSON.parse(ev.data);
    refreshStats();
    refreshStatus();
    refreshThreadTable();
    if (simState.events.length !== lastEventCount) {
      lastEventCount = simState.events.length;
      localLog = [...simState.events];
      refreshLog();
    }
  };

  ws.onclose = () => setStatus('Conexão encerrada. Recarregue a página.');
  ws.onerror = () => setStatus(`Erro ao conectar (porta ${BACKEND_PORT}).`);
}

// ── Controles ─────────────────────────────────────────────────────────────────
btnStart.addEventListener('click', async () => {
  const n     = parseInt(inputCars.value) || 4;
  const delay = parseFloat(sliderDelay.value);
  localLog = [];
  lastEventCount = 0;
  await fetch(`${BACKEND_HTTP}/api/start`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ num_cars: n, max_delay: delay }),
  });
});

btnReset.addEventListener('click', async () => {
  await fetch(`${BACKEND_HTTP}/api/reset`, { method: 'POST' });
  localLog = [];
  lastEventCount = 0;
  threadTbody.innerHTML = '<tr><td colspan="5" class="empty-row">Nenhuma thread ativa</td></tr>';
  logList.innerHTML = '<span class="log-empty">Nenhum evento ainda...</span>';
});

btnClearLog.addEventListener('click', () => {
  localLog = [];
  logList.innerHTML = '<span class="log-empty">Log limpo.</span>';
});

// ── Estatísticas ──────────────────────────────────────────────────────────────
function refreshStats() {
  const s = simState.stats;
  elTotal.textContent      = s.total;
  elActive.textContent     = s.active;
  elFinished.textContent   = s.finished;
  elCollisions.textContent = s.collisions;
}

function setStatus(msg) { elStatus.textContent = msg; }

function refreshStatus() {
  const s = simState.stats;
  if (!simState.running && s.total === 0) {
    setStatus('Aguardando início...');
  } else if (simState.running && s.active > 0) {
    setStatus(`Em andamento — ${s.active} thread(s) ativa(s).`);
  } else if (s.total > 0 && s.active === 0) {
    setStatus(s.collisions > 0
      ? `Concluída. ${s.collisions} colisão(ões) — sem mutex = sem proteção.`
      : `Concluída SEM colisões desta vez. Execute novamente para ver a variação.`);
  }
}

// ── Tabela de threads ─────────────────────────────────────────────────────────
const STATE_LABEL = {
  moving:      '● movendo',
  in_critical: '● região crítica',
  collided:    '● colidiu',
  finished:    '● concluído',
};

const DIR_LABEL = { north: '↓', south: '↑', west: '→', east: '←' };

function refreshThreadTable() {
  if (!simState.cars.length) return;
  threadTbody.innerHTML = simState.cars.map(car => `
    <tr>
      <td>${car.id}</td>
      <td>${DIR_LABEL[car.direction] ?? car.direction}</td>
      <td class="ts-${car.state}">${STATE_LABEL[car.state] ?? car.state}</td>
      <td>${car.quadrant || '—'}${car.time_in_critical > 0 ? ' · ' + car.time_in_critical.toFixed(1) + 's' : ''}</td>
      <td>${car.speed ? car.speed.toFixed(1) : '—'}</td>
    </tr>`).join('');
}

// ── Log de eventos ────────────────────────────────────────────────────────────
function refreshLog() {
  if (!localLog.length) {
    logList.innerHTML = '<span class="log-empty">Nenhum evento ainda...</span>';
    return;
  }
  logList.innerHTML = [...localLog].reverse()
    .map(ev => `<div class="log-entry log-${ev.type}">[${ev.time.toFixed(2).padStart(6)}s] ${ev.message}</div>`)
    .join('');
}

// ── Canvas: utilitários ───────────────────────────────────────────────────────
function rRect(x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(x, y, w, h, r);
  } else {
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y,     x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x,     y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x,     y,     x + r, y);
    ctx.closePath();
  }
}

// ── Canvas: pista ─────────────────────────────────────────────────────────────
function drawRoad() {
  // Fundo
  ctx.fillStyle = '#091a3a';   // fundo — bg Inatel
  ctx.fillRect(0, 0, W, H);

  // Asfalto
  ctx.fillStyle = '#374151';
  ctx.fillRect(CX - ROAD_HALF, 0,  ROAD_HALF * 2, H);   // vertical
  ctx.fillRect(0, CY - ROAD_HALF,  W, ROAD_HALF * 2);   // horizontal

  ctx.save();

  // Bordas externas das vias
  ctx.strokeStyle = '#6b7280';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([]);
  ctx.beginPath();
  // Via vertical: bordas esquerda e direita (fora da região crítica)
  ctx.moveTo(CX - ROAD_HALF, 0);   ctx.lineTo(CX - ROAD_HALF, CY1);
  ctx.moveTo(CX - ROAD_HALF, CY2); ctx.lineTo(CX - ROAD_HALF, H);
  ctx.moveTo(CX + ROAD_HALF, 0);   ctx.lineTo(CX + ROAD_HALF, CY1);
  ctx.moveTo(CX + ROAD_HALF, CY2); ctx.lineTo(CX + ROAD_HALF, H);
  // Via horizontal: bordas superior e inferior
  ctx.moveTo(0,   CY - ROAD_HALF); ctx.lineTo(CX1, CY - ROAD_HALF);
  ctx.moveTo(CX2, CY - ROAD_HALF); ctx.lineTo(W,   CY - ROAD_HALF);
  ctx.moveTo(0,   CY + ROAD_HALF); ctx.lineTo(CX1, CY + ROAD_HALF);
  ctx.moveTo(CX2, CY + ROAD_HALF); ctx.lineTo(W,   CY + ROAD_HALF);
  ctx.stroke();

  // Divisor central entre pistas (tracejado, fora da região crítica)
  ctx.strokeStyle = '#4b5563';
  ctx.lineWidth = 1;
  ctx.setLineDash([10, 8]);
  ctx.beginPath();
  // Divisor da via vertical (x = 250)
  ctx.moveTo(CX, 0);   ctx.lineTo(CX, CY1);
  ctx.moveTo(CX, CY2); ctx.lineTo(CX, H);
  // Divisor da via horizontal (y = 250)
  ctx.moveTo(0,   CY); ctx.lineTo(CX1, CY);
  ctx.moveTo(CX2, CY); ctx.lineTo(W,   CY);
  ctx.stroke();

  ctx.restore();

  // Setas de direção por pista
  ctx.font = 'bold 16px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // NORTH (↓): pista esquerda da via vertical (x=220)
  ctx.fillStyle = 'rgba(59,130,246,0.35)';
  ctx.fillText('▼', LANE.north.x, 55);
  ctx.fillText('▼', LANE.north.x, 115);
  ctx.fillText('▼', LANE.north.x, H - 115);
  ctx.fillText('▼', LANE.north.x, H - 55);

  // SOUTH (↑): pista direita da via vertical (x=280)
  ctx.fillStyle = 'rgba(168,85,247,0.35)';
  ctx.fillText('▲', LANE.south.x, 55);
  ctx.fillText('▲', LANE.south.x, 115);
  ctx.fillText('▲', LANE.south.x, H - 115);
  ctx.fillText('▲', LANE.south.x, H - 55);

  // WEST (►): pista superior da via horizontal (y=220)
  ctx.fillStyle = 'rgba(59,130,246,0.35)';
  ctx.fillText('►', 55,      LANE.west.y);
  ctx.fillText('►', 115,     LANE.west.y);
  ctx.fillText('►', W - 115, LANE.west.y);
  ctx.fillText('►', W - 55,  LANE.west.y);

  // EAST (◄): pista inferior da via horizontal (y=280)
  ctx.fillStyle = 'rgba(168,85,247,0.35)';
  ctx.fillText('◄', 55,      LANE.east.y);
  ctx.fillText('◄', 115,     LANE.east.y);
  ctx.fillText('◄', W - 115, LANE.east.y);
  ctx.fillText('◄', W - 55,  LANE.east.y);
}

// ── Canvas: região crítica (4 quadrantes) ────────────────────────────────────
//
//   Q1 (top-left)     NORTH × WEST    cor azul
//   Q2 (top-right)    SOUTH × WEST    cor âmbar
//   Q3 (bottom-left)  NORTH × EAST    cor verde
//   Q4 (bottom-right) SOUTH × EAST    cor roxo
//
const MX = W / 2;  // 250 — divisor horizontal dos quadrantes
const MY = H / 2;  // 250 — divisor vertical dos quadrantes

const QUAD_META = [
  { name: 'Q1', label: 'N×W', x: CX1, y: CY1, w: MX - CX1, h: MY - CY1, fill: 'rgba(59,130,246,0.10)',  stroke: 'rgba(59,130,246,0.5)'  },
  { name: 'Q2', label: 'S×W', x: MX,  y: CY1, w: CX2 - MX, h: MY - CY1, fill: 'rgba(245,158,11,0.10)', stroke: 'rgba(245,158,11,0.5)'  },
  { name: 'Q3', label: 'N×E', x: CX1, y: MY,  w: MX - CX1, h: CY2 - MY, fill: 'rgba(34,197,94,0.10)',  stroke: 'rgba(34,197,94,0.5)'   },
  { name: 'Q4', label: 'S×E', x: MX,  y: MY,  w: CX2 - MX, h: CY2 - MY, fill: 'rgba(168,85,247,0.10)', stroke: 'rgba(168,85,247,0.5)'  },
];

function drawCriticalRegion() {
  // Fundo por quadrante
  QUAD_META.forEach(q => {
    ctx.fillStyle = q.fill;
    ctx.fillRect(q.x, q.y, q.w, q.h);
  });

  // Linhas divisórias internas (tracejadas)
  ctx.save();
  ctx.setLineDash([5, 4]);
  ctx.strokeStyle = 'rgba(255,255,255,0.12)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(MX, CY1); ctx.lineTo(MX, CY2);  // divisor vertical
  ctx.moveTo(CX1, MY); ctx.lineTo(CX2, MY);   // divisor horizontal
  ctx.stroke();
  ctx.restore();

  // Borda externa da região crítica
  ctx.save();
  ctx.setLineDash([7, 5]);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(CX1 + 1, CY1 + 1, CX2 - CX1 - 2, CY2 - CY1 - 2);
  ctx.restore();

  // Rótulos por quadrante (nome + pares de direção)
  ctx.font = 'bold 9px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  QUAD_META.forEach(q => {
    ctx.fillStyle = q.stroke;
    ctx.fillText(q.name,  q.x + q.w / 2, q.y + q.h / 2 - 6);
    ctx.fillText(q.label, q.x + q.w / 2, q.y + q.h / 2 + 6);
  });

  // Título acima da região
  ctx.fillStyle = 'rgba(239,68,68,0.6)';
  ctx.font = 'bold 10px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText('REGIÃO CRÍTICA', (CX1 + CX2) / 2, CY1 - 6);
}

// ── Canvas: carro ─────────────────────────────────────────────────────────────
function drawCar(car) {
  if (car.state === 'finished') return;

  const vertical = car.direction === 'north' || car.direction === 'south';
  const cw = vertical ? 14 : 22;
  const ch = vertical ? 22 : 14;
  const x  = car.x - cw / 2;
  const y  = car.y - ch / 2;

  // Sombra
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  rRect(x + 2, y + 2, cw, ch, 3);
  ctx.fill();

  // Corpo
  ctx.fillStyle = COLORS[car.state] || COLORS.moving;
  rRect(x, y, cw, ch, 3);
  ctx.fill();

  // Para-brisa
  ctx.fillStyle = 'rgba(255,255,255,0.2)';
  if (vertical) {
    ctx.fillRect(x + 3, y + 3, cw - 6, ch * 0.38);
  } else {
    ctx.fillRect(x + 3, y + 3, cw * 0.38, ch - 6);
  }

  // Explosão para carros colididos
  if (car.state === 'collided') {
    ctx.font = '26px serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('💥', car.x, car.y);
  }
}

// ── Loop de renderização ──────────────────────────────────────────────────────
function render() {
  drawRoad();
  drawCriticalRegion();
  simState.cars.forEach(drawCar);
  requestAnimationFrame(render);
}

// ── Inicialização ─────────────────────────────────────────────────────────────
connect();
render();
