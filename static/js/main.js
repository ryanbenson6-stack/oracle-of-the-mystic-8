/* ============================================================
   ORACLE OF THE MYSTIC 8 — Main JS
   ============================================================ */

// ---- State ----
const STATE = { IDLE: 'idle', LOADING: 'loading', REVEALING: 'revealing', DISPLAYED: 'displayed' };
let currentState = STATE.IDLE;
let currentReading = null; // { question, ball, answer }

// ---- DOM Refs ----
const eightBall      = document.getElementById('eight-ball');
const ballAnswer     = document.getElementById('ball-answer');
const questionInput  = document.getElementById('question-input');
const submitBtn      = document.getElementById('submit-btn');
const charCounter    = document.getElementById('char-counter');
const readingSection = document.getElementById('reading-section');
const smokeContainer = document.getElementById('smoke-container');
const readingText    = document.getElementById('reading-text');
const shareRow       = document.getElementById('share-row');
const shareBtn       = document.getElementById('share-btn');
const shameBtn       = document.getElementById('shame-btn');
const shareConfirm   = document.getElementById('share-confirm');

// ---- Starfield Canvas ----
const canvas = document.getElementById('starfield');
const ctx    = canvas.getContext('2d');
let stars    = [];

const STAR_COUNT  = 160;
const NEON_COLORS = ['#bf00ff', '#00ffff', '#ff00ff', '#b8d4ff'];

function initStars() {
  stars = [];
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 1.5 + 0.3,
      phase: Math.random() * Math.PI * 2,
      speed: Math.random() * 0.004 + 0.001,
      color: Math.random() < 0.08 ? NEON_COLORS[Math.floor(Math.random() * NEON_COLORS.length)] : '#ffffff',
      baseOpacity: Math.random() * 0.6 + 0.2,
    });
  }
}

function resizeCanvas() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  initStars();
}

function animateStars() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (const star of stars) {
    star.phase += star.speed;
    const opacity = star.baseOpacity * (0.5 + 0.5 * Math.sin(star.phase));
    ctx.globalAlpha = opacity;
    ctx.fillStyle   = star.color;
    ctx.beginPath();
    ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  requestAnimationFrame(animateStars);
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(resizeCanvas, 250);
});

resizeCanvas();
requestAnimationFrame(animateStars);
eightBall.classList.add('idle-float');

// ---- Char Counter ----
questionInput.addEventListener('input', () => {
  const len = questionInput.value.length;
  charCounter.textContent = `${len} / 500`;
  charCounter.style.color = len > 450 ? 'rgba(255,80,80,0.8)' : 'rgba(0,255,65,0.4)';
});

// ---- Enter to Submit ----
questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (currentState === STATE.IDLE || currentState === STATE.DISPLAYED) handleSubmit();
  }
});

submitBtn.addEventListener('click', handleSubmit);

// ---- State Machine ----
function setState(state) {
  currentState = state;
  const isLoading = state === STATE.LOADING;
  submitBtn.disabled = isLoading || state === STATE.REVEALING;
  questionInput.disabled = isLoading;
  submitBtn.textContent = isLoading ? '✦ CONSULTING... ✦' : '✦ CONSULT THE SPHERE ✦';
}

// ---- Main Submit Handler ----
async function handleSubmit() {
  const question = questionInput.value.trim();
  if (!question) return;

  setState(STATE.LOADING);
  currentReading = null;

  // Ripple
  const ripple = document.createElement('div');
  ripple.className = 'ripple-ring';
  document.querySelector('.eight-ball-section').appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());

  // Shake + surge
  eightBall.classList.remove('shaking', 'surging', 'idle-float');
  void eightBall.offsetWidth;
  eightBall.classList.add('surging');

  ballAnswer.innerHTML = '<span class="loading-dots">· · ·</span>';

  // Reset reading
  readingSection.classList.remove('visible');
  smokeContainer.classList.remove('smoke-reveal');
  readingText.style.opacity = '0';
  readingText.textContent = '';
  shareRow.classList.remove('visible');
  shameBtn.disabled = false;
  shameBtn.textContent = '🔥 SHAME THIS READING';

  const [result] = await Promise.all([fetchOracle(question), delay(2500)]);

  currentReading = { question, ball: result.ball, answer: result.answer };

  ballAnswer.textContent = result.ball;
  ballAnswer.style.animation = 'answerFadeIn 0.6s ease forwards';

  readingSection.classList.add('visible');
  smokeContainer.classList.add('smoke-reveal');
  setState(STATE.REVEALING);

  readingText.style.opacity = '1';
  readingText.textContent = result.answer;

  await delay(1400);
  readingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  await delay(2800);
  shareRow.classList.add('visible');

  setState(STATE.DISPLAYED);
  eightBall.classList.remove('surging');
  eightBall.classList.add('idle-float');
}

// ---- API Call ----
async function fetchOracle(question) {
  const fallback = { ball: 'the sphere is silent.', answer: 'The cosmic signal is lost. Seek guidance again.' };
  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (data.error) return fallback;
    return { ball: data.ball, answer: data.answer };
  } catch {
    return fallback;
  }
}

// ---- Share Button ----
shareBtn.addEventListener('click', async () => {
  const url = window.location.href;
  const shareText = 'I consulted the Oracle of the Mystic 8 and the sphere had OPINIONS. Ask it your question 🔮';
  if (navigator.share) {
    try { await navigator.share({ title: 'Oracle of the Mystic 8', text: shareText, url }); return; }
    catch { /* cancelled */ }
  }
  try {
    await navigator.clipboard.writeText(url);
    shareConfirm.textContent = '✦ link copied. unleash it. ✦';
  } catch {
    shareConfirm.textContent = '✦ ' + url + ' ✦';
  }
  shareConfirm.classList.add('show');
  setTimeout(() => shareConfirm.classList.remove('show'), 3000);
});

// ---- Shame Button ----
shameBtn.addEventListener('click', async () => {
  if (!currentReading) return;
  shameBtn.disabled = true;
  shameBtn.textContent = '🔥 RECORDING...';
  try {
    const res = await fetch('/api/shame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentReading),
    });
    const data = await res.json();
    if (data.success) {
      shameBtn.textContent = '🔥 SHAMEFULLY RECORDED';
      loadHall(); // refresh the hall
    } else {
      shameBtn.textContent = '🔥 SHAME THIS READING';
      shameBtn.disabled = false;
    }
  } catch {
    shameBtn.textContent = '🔥 SHAME THIS READING';
    shameBtn.disabled = false;
  }
});

// ---- Hall of Shame ----
const hallRecent = document.getElementById('hall-recent');
const hallTop    = document.getElementById('hall-top');
const hallTabs   = document.querySelectorAll('.hall-tab');
let allEntries   = [];
let scorched     = JSON.parse(localStorage.getItem('scorched') || '[]'); // voted IDs

hallTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    hallTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const which = tab.dataset.tab;
    hallRecent.style.display = which === 'recent' ? 'flex' : 'none';
    hallTop.style.display    = which === 'top'    ? 'flex' : 'none';
  });
});

function timeAgo(ts) {
  const diff = Math.floor(Date.now() / 1000) - ts;
  if (diff < 60)   return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function buildCard(entry) {
  const voted = scorched.includes(entry.id);
  const card  = document.createElement('div');
  card.className = 'shame-card';
  card.innerHTML = `
    <div class="shame-question">${escHtml(entry.question)}</div>
    <div class="shame-ball">${escHtml(entry.ball)}</div>
    <div class="shame-answer">${escHtml(entry.answer)}</div>
    <div class="shame-footer">
      <span class="shame-time">${timeAgo(entry.timestamp)}</span>
      <button class="burn-btn ${voted ? 'scorched' : ''}" data-id="${entry.id}">
        🔥 ${entry.burns || 0} SCORCHED
      </button>
    </div>
  `;
  const btn = card.querySelector('.burn-btn');
  if (!voted) {
    btn.addEventListener('click', () => burnEntry(entry.id, btn));
  }
  return card;
}

function renderHall() {
  // Recent: newest first, top 10
  const recent = [...allEntries].slice(0, 10);
  // Top: sorted by burns, top 10
  const top = [...allEntries].sort((a, b) => (b.burns || 0) - (a.burns || 0)).slice(0, 10);

  hallRecent.innerHTML = '';
  hallTop.innerHTML    = '';

  if (recent.length === 0) {
    hallRecent.innerHTML = '<div class="hall-empty">No readings shamed yet. The sphere is judging you.</div>';
    hallTop.innerHTML    = '<div class="hall-empty">No readings shamed yet. The sphere is judging you.</div>';
    return;
  }

  recent.forEach(e => hallRecent.appendChild(buildCard(e)));
  top.forEach(e => hallTop.appendChild(buildCard(e)));
}

async function loadHall() {
  try {
    const res = await fetch('/api/hall-of-shame');
    allEntries = await res.json();
    renderHall();
  } catch { /* no upstash — silently skip */ }
}

async function burnEntry(id, btn) {
  btn.disabled = true;
  try {
    const res  = await fetch(`/api/burn/${id}`, { method: 'POST' });
    const data = await res.json();
    // Update local entry
    const entry = allEntries.find(e => e.id === id);
    if (entry) entry.burns = data.burns;
    // Save to localStorage
    scorched.push(id);
    localStorage.setItem('scorched', JSON.stringify(scorched));
    btn.textContent = `🔥 ${data.burns} SCORCHED`;
    btn.classList.add('scorched');
    // Re-sort top list
    renderHall();
  } catch {
    btn.disabled = false;
  }
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ---- Utility ----
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---- Init ----
loadHall();
