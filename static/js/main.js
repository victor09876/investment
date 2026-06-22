// InvestPro Main JS
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

// Toast
function showToast(msg, type='success', duration=3500) {
  let c = $('#toast-container');
  if (!c) { c = document.createElement('div'); c.id='toast-container'; document.body.appendChild(c); }
  const colors = {success:'var(--green)',danger:'var(--red)',warning:'var(--amber)',info:'var(--blue)'};
  const icons  = {success:'✓',danger:'✕',warning:'⚠',info:'ℹ'};
  const el = document.createElement('div');
  el.className = 'toast-item';
  el.style.borderLeftColor = colors[type]||colors.success;
  el.innerHTML = `<span style="color:${colors[type]||colors.success};margin-right:7px;font-weight:700;">${icons[type]||icons.success}</span>${msg}`;
  c.appendChild(el);
  setTimeout(() => { el.style.opacity='0'; el.style.transform='translateX(100px)'; el.style.transition='.3s'; setTimeout(()=>el.remove(),350); }, duration);
}

// Modal
function openModal(id) { const m=$(`#${id}`); if(m){m.classList.add('open');document.body.style.overflow='hidden';} }
function closeModal(id) { const m=$(`#${id}`); if(m){m.classList.remove('open');document.body.style.overflow='';} }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) { e.target.classList.remove('open'); document.body.style.overflow=''; }
  if (e.target.classList.contains('modal-close')) { const o=e.target.closest('.modal-overlay'); if(o){o.classList.remove('open');document.body.style.overflow='';} }
});

// Sidebar mobile
function initSidebar() {
  const sb=$('#sidebar'), ov=$('#sidebar-overlay'), hb=$('#hamburger');
  if (!sb) return;
  hb?.addEventListener('click', ()=>{ sb.classList.toggle('open'); ov?.classList.toggle('open'); });
  ov?.addEventListener('click', ()=>{ sb.classList.remove('open'); ov.classList.remove('open'); });
}

// Tabs
function initTabs() {
  $$('.tabs').forEach(tabs => {
    const btns = $$('.tab-btn', tabs);
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        const wrap = tabs.closest('.tabs-wrap') || document;
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        $$('.tab-panel', wrap).forEach(p => p.style.display='none');
        const target = $(`#tab-${btn.dataset.tab}`, wrap);
        if (target) target.style.display='';
      });
    });
  });
}

// Progress bar animate
function animateProgress() {
  $$('[data-progress]').forEach(bar => {
    const pct = parseFloat(bar.dataset.progress);
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = pct + '%'; }, 150);
  });
}

// Number animate
function animateNumbers() {
  $$('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const dec    = el.dataset.dec || 0;
    const start  = performance.now();
    const duration = 900;
    const step = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + (target * ease).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

// Professional bar chart powered by Chart.js
// `data`: array of {value, label}. `color`: CSS color (resolved from CSS var if needed).
// `options.isCurrency`: format y-axis/tooltips as $. `options.colorVar`: name for resolved theme color.
const _chartInstances = {};
function _resolveColor(color) {
  if (typeof color === 'string' && color.startsWith('var(')) {
    const varName = color.slice(4, -1).trim();
    const resolved = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    return resolved || '#5EEAD4';
  }
  return color;
}
function drawBarChart(containerId, data, color='var(--gold)', options={}) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const resolvedColor = _resolveColor(color);
  const isCurrency = options.isCurrency !== false; // default true for backward compat

  // Ensure a canvas exists inside the container
  let canvas = container.querySelector('canvas');
  if (!canvas) {
    canvas = document.createElement('canvas');
    container.innerHTML = '';
    container.style.position = 'relative';
    container.style.height = container.style.height || '220px';
    container.appendChild(canvas);
  }

  // Destroy previous instance on this canvas if re-rendering
  if (_chartInstances[containerId]) {
    _chartInstances[containerId].destroy();
  }

  const gridColor = 'rgba(255,255,255,.05)';
  const textColor = getComputedStyle(document.documentElement).getPropertyValue('--faint').trim() || '#4D5868';
  const fmt = (v) => isCurrency
    ? (v >= 1000 ? '$' + (v/1000).toFixed(v % 1000 === 0 ? 0 : 1) + 'k' : '$' + v.toLocaleString())
    : v.toLocaleString();

  // Build a subtle gradient fill
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, resolvedColor);
  gradient.addColorStop(1, resolvedColor + '22');

  _chartInstances[containerId] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.map(d => d.label),
      datasets: [{
        data: data.map(d => d.value),
        backgroundColor: gradient,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 42,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#141B26',
          borderColor: 'rgba(94,234,212,.2)',
          borderWidth: 1,
          titleColor: '#F5F7FA',
          bodyColor: '#8B96A8',
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            label: (ctx) => fmt(ctx.parsed.y)
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor, drawTicks: false },
          border: { display: false },
          ticks: {
            color: textColor,
            font: { family: "'JetBrains Mono', monospace", size: 11 },
            callback: (v) => fmt(v),
            maxTicksLimit: 5,
          }
        }
      }
    }
  });
}

// Copy to clipboard
function copyText(text, label='Copied!') {
  navigator.clipboard?.writeText(text).then(()=>showToast(label)).catch(()=>{
    const t = document.createElement('textarea'); t.value=text; document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t); showToast(label);
  });
}

// Password strength
function initPasswordStrength(inputId, barId, labelId) {
  const inp = $(`#${inputId}`), bar = $(`#${barId}`), lbl = $(`#${labelId}`);
  if (!inp || !bar) return;
  inp.addEventListener('input', () => {
    const pw = inp.value;
    let s = 0;
    if (pw.length >= 8) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    const pcts  = [0,25,50,75,100];
    const cols  = ['','var(--red)','var(--amber)','var(--amber)','var(--green)'];
    const texts = ['','Weak','Fair','Good','Strong'];
    bar.style.width = pcts[s]+'%';
    bar.style.background = cols[s]||cols[1];
    if (lbl) lbl.textContent = texts[s] || '';
  });
}

// Method card select
function initMethodCards() {
  $$('.method-card').forEach(card => {
    card.addEventListener('click', () => {
      const group = card.closest('.method-grid');
      $$('.method-card', group).forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      const target = card.dataset.target;
      if (target) {
        const wrap = card.closest('.method-section') || document;
        $$('.method-detail', wrap).forEach(d => d.style.display='none');
        const detail = $(`#${target}`, wrap) || $(`#${target}`);
        if (detail) detail.style.display='';
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initTabs();
  animateProgress();
  animateNumbers();
  initMethodCards();
});
