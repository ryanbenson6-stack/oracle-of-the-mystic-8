/* ============================================================
   ORACLE OF THE MYSTIC 8 — Main JS
   ============================================================ */

// ---- State ----
const STATE = { IDLE: 'idle', LOADING: 'loading', REVEALING: 'revealing', DISPLAYED: 'displayed' };
let currentState = STATE.IDLE;

// ---- DOM Refs ----
const eightBall    = document.getElementById('eight-ball');
const ballAnswer   = document.getElementById('ball-answer');
const questionInput = document.getElementById('question-input');
const submitBtn    = document.getElementById('submit-btn');
const charCounter  = document.getElementById('char-counter');
const readingSection = document.getElementById('reading-section');
const smokeContainer = document.getElementById('smoke-container');
const readingText  = document.getElementById('reading-text');
const shareRow     = document.getElementById('share-row');
const shareBtn     = document.getElementById('share-btn');
const shareConfirm = document.getElementById('share-confirm');

// ---- Starfield Canvas ----
const canvas = document.getElementById('starfield');
const ctx    = canvas.getContext('2d');
let stars    = [];

const STAR_COUNT   = 160;
const NEON_COLORS  = ['#bf00ff', '#00ffff', '#ff00ff', '#b8d4ff'];

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

function animateStars(ts) {
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

// ---- Idle Float ----
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
    if (currentState === STATE.IDLE || currentState === STATE.DISPLAYED) {
      handleSubmit();
    }
  }
});

submitBtn.addEventListener('click', handleSubmit);

// ---- State Machine ----
function setState(state) {
  currentState = state;
  const isLoading = state === STATE.LOADING;
  submitBtn.disabled = isLoading || state === STATE.REVEALING;
  questionInput.disabled = isLoading;
  if (isLoading) {
    submitBtn.textContent = '✦ CONSULTING... ✦';
  } else {
    submitBtn.textContent = '✦ CONSULT THE SPHERE ✦';
  }
}

// ---- Main Submit Handler ----
async function handleSubmit() {
  const question = questionInput.value.trim();
  if (!question) return;

  setState(STATE.LOADING);

  // Ripple ring effect
  const ripple = document.createElement('div');
  ripple.className = 'ripple-ring';
  document.querySelector('.eight-ball-section').appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());

  // Shake + surge the ball
  eightBall.classList.remove('shaking', 'surging', 'idle-float');
  void eightBall.offsetWidth; // force reflow
  eightBall.classList.add('surging');

  ballAnswer.innerHTML = '<span class="loading-dots">· · ·</span>';

  // Clear previous reading
  readingSection.classList.remove('visible');
  smokeContainer.classList.remove('smoke-reveal');
  readingText.style.opacity = '0';
  readingText.textContent = '';
  shareRow.classList.remove('visible');

  // Fire API call + enforce minimum 2.5s for shake
  const [result] = await Promise.all([
    fetchOracle(question),
    delay(2500),
  ]);

  // Show ball verdict text
  ballAnswer.textContent = result.ball;
  ballAnswer.style.animation = 'answerFadeIn 0.6s ease forwards';

  // Reveal reading section with smoke
  readingSection.classList.add('visible');
  smokeContainer.classList.add('smoke-reveal');

  setState(STATE.REVEALING);

  // Set full reading text — CSS smoke animation reveals it
  readingText.style.opacity = '1';
  readingText.textContent = result.answer;

  // Longer pause before scrolling down
  await delay(1400);
  readingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Wait for smoke reveal to finish, then show share button
  await delay(2800);
  shareRow.classList.add('visible');

  setState(STATE.DISPLAYED);

  eightBall.classList.remove('surging');
  eightBall.classList.add('idle-float');
}

// ---- API Call ----
async function fetchOracle(question) {
  const fallback = { ball: 'the sphere is silent.', answer: 'The cosmic signal is lost... the vibrations are unclear. Seek guidance again.' };
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
    try {
      await navigator.share({ title: 'Oracle of the Mystic 8', text: shareText, url });
      return;
    } catch { /* user cancelled — fall through */ }
  }

  // Fallback: copy to clipboard
  try {
    await navigator.clipboard.writeText(url);
    shareConfirm.textContent = '✦ link copied. unleash it. ✦';
  } catch {
    shareConfirm.textContent = '✦ copy this: ' + url + ' ✦';
  }

  shareConfirm.classList.add('show');
  setTimeout(() => shareConfirm.classList.remove('show'), 3000);
});

// ---- Utility ----
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
