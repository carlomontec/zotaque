"""
Interactive Apple-Style Vehicle Motion Cues Overlay with Live GUI Config Panel.
Runs seamlessly in any browser, Steam Game Mode web view, or Decky overlay.
"""

OVERLAY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Zotaque Motion Cues</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body, html {
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #fff;
  }
  #motionCanvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    display: block;
    pointer-events: none;
  }
  /* Top Bar / Telemetry */
  #topBar {
    position: absolute;
    top: 14px;
    left: 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    z-index: 100;
  }
  .badge {
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00ff88;
    box-shadow: 0 0 8px #00ff88;
  }
  .settings-btn {
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #fff;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .settings-btn:hover {
    background: rgba(30, 41, 59, 0.95);
    border-color: #00e5ff;
    transform: scale(1.03);
  }
  /* Settings Modal / Glassmorphic Panel */
  #settingsPanel {
    position: absolute;
    top: 60px;
    left: 14px;
    width: 320px;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    z-index: 1000;
    display: none;
    max-height: calc(100vh - 80px);
    overflow-y: auto;
  }
  #settingsPanel.active { display: block; }
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 8px;
  }
  .panel-title { font-size: 14px; font-weight: 700; color: #00e5ff; }
  .close-btn {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 18px;
    cursor: pointer;
  }
  .setting-row { margin-bottom: 14px; }
  .setting-label {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 500;
    color: #cbd5e1;
    margin-bottom: 6px;
  }
  .slider {
    width: 100%;
    -webkit-appearance: none;
    height: 6px;
    border-radius: 3px;
    background: #334155;
    outline: none;
  }
  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #00e5ff;
    cursor: pointer;
    box-shadow: 0 0 8px #00e5ff;
  }
  .color-picker {
    display: flex;
    gap: 8px;
    margin-top: 6px;
  }
  .color-dot {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    cursor: pointer;
    border: 2px solid transparent;
    transition: transform 0.15s;
  }
  .color-dot.active { border-color: #fff; transform: scale(1.15); }
  .telemetry-box {
    margin-top: 14px;
    background: rgba(0, 0, 0, 0.35);
    padding: 10px;
    border-radius: 8px;
    font-family: monospace;
    font-size: 11px;
    color: #94a3b8;
  }
</style>
</head>
<body>

<canvas id="motionCanvas"></canvas>

<div id="topBar">
  <div class="badge">
    <div class="status-dot" id="statusDot"></div>
    <span id="statusText">ZOTAQUE CUES</span>
  </div>
  <button class="settings-btn" id="toggleSettings">⚙ Config</button>
</div>

<div id="settingsPanel">
  <div class="panel-header">
    <span class="panel-title">Motion Cues Calibration</span>
    <button class="close-btn" id="closeSettings">✕</button>
  </div>

  <div class="setting-row">
    <div class="setting-label">
      <span>Tilt Sensitivity</span>
      <span id="valTilt">1.0</span>
    </div>
    <input type="range" class="slider" id="sliderTilt" min="0" max="3" step="0.1" value="1.0">
  </div>

  <div class="setting-row">
    <div class="setting-label">
      <span>Dynamic Sensitivity</span>
      <span id="valDyn">1.2</span>
    </div>
    <input type="range" class="slider" id="sliderDyn" min="0.2" max="3" step="0.1" value="1.2">
  </div>

  <div class="setting-row">
    <div class="setting-label">
      <span>Vibration Smoothing</span>
      <span id="valSmooth">85%</span>
    </div>
    <input type="range" class="slider" id="sliderSmooth" min="0.3" max="0.95" step="0.05" value="0.85">
  </div>

  <div class="setting-row">
    <div class="setting-label">
      <span>Max Dot Shift (px)</span>
      <span id="valShift">50px</span>
    </div>
    <input type="range" class="slider" id="sliderShift" min="20" max="120" step="5" value="50">
  </div>

  <div class="setting-row">
    <div class="setting-label">
      <span>Dot Size & Opacity</span>
      <span id="valDot">6px</span>
    </div>
    <input type="range" class="slider" id="sliderDotSize" min="3" max="14" step="1" value="6">
  </div>

  <div class="setting-row">
    <div class="setting-label">Dot Accent Color</div>
    <div class="color-picker">
      <div class="color-dot active" style="background: #00e5ff;" data-color="#00e5ff"></div>
      <div class="color-dot" style="background: #00ff88;" data-color="#00ff88"></div>
      <div class="color-dot" style="background: #ff007f;" data-color="#ff007f"></div>
      <div class="color-dot" style="background: #ffaa00;" data-color="#ffaa00"></div>
      <div class="color-dot" style="background: #ffffff;" data-color="#ffffff"></div>
    </div>
  </div>

  <div class="telemetry-box" id="telemetry">
    DX: +0.00 | DY: +0.00<br>
    AX: 0.00 | AY: 0.00 | AZ: 9.81
  </div>
</div>

<script>
  const canvas = document.getElementById('motionCanvas');
  const ctx = canvas.getContext('2d');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const toggleBtn = document.getElementById('toggleSettings');
  const closeBtn = document.getElementById('closeSettings');
  const panel = document.getElementById('settingsPanel');
  const telemetry = document.getElementById('telemetry');

  // Sliders
  const sTilt = document.getElementById('sliderTilt');
  const sDyn = document.getElementById('sliderDyn');
  const sSmooth = document.getElementById('sliderSmooth');
  const sShift = document.getElementById('sliderShift');
  const sDotSize = document.getElementById('sliderDotSize');

  let width = window.innerWidth;
  let height = window.innerHeight;
  canvas.width = width;
  canvas.height = height;

  window.addEventListener('resize', () => {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
    initDots();
  });

  toggleBtn.onclick = () => panel.classList.toggle('active');
  closeBtn.onclick = () => panel.classList.remove('active');

  // Config State
  let config = {
    tilt_sensitivity: 1.0,
    dynamic_sensitivity: 1.2,
    smoothing: 0.85,
    max_shift_px: 50,
    dot_radius: 6,
    dot_color: '#00e5ff',
    dot_count_edge: 8
  };

  // Color picker
  document.querySelectorAll('.color-dot').forEach(el => {
    el.onclick = () => {
      document.querySelectorAll('.color-dot').forEach(d => d.classList.remove('active'));
      el.classList.add('active');
      config.dot_color = el.getAttribute('data-color');
      saveConfig();
    };
  });

  function bindSlider(slider, labelEl, key, suffix = '', transform = x => x) {
    slider.oninput = () => {
      config[key] = parseFloat(slider.value);
      labelEl.textContent = transform(slider.value) + suffix;
      saveConfig();
    };
  }

  bindSlider(sTilt, document.getElementById('valTilt'), 'tilt_sensitivity');
  bindSlider(sDyn, document.getElementById('valDyn'), 'dynamic_sensitivity');
  bindSlider(sSmooth, document.getElementById('valSmooth'), 'smoothing', '%', v => Math.round(v * 100));
  bindSlider(sShift, document.getElementById('valShift'), 'max_shift_px', 'px');
  bindSlider(sDotSize, document.getElementById('valDot'), 'dot_radius', 'px');

  function saveConfig() {
    fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    }).catch(() => {});
  }

  // Dot Layout
  const dots = [];
  function initDots() {
    dots.length = 0;
    const margin = 28;
    const count = config.dot_count_edge;

    // Top & Bottom
    for (let i = 0; i < count; i++) {
      const x = margin + ((width - margin * 2) / (count - 1)) * i;
      dots.push({ base_x: x, base_y: margin, x: x, y: margin });
      dots.push({ base_x: x, base_y: height - margin, x: x, y: height - margin });
    }
    // Left & Right
    for (let i = 1; i < count - 1; i++) {
      const y = margin + ((height - margin * 2) / (count - 1)) * i;
      dots.push({ base_x: margin, base_y: y, x: margin, y: y });
      dots.push({ base_x: width - margin, base_y: y, x: width - margin, y: y });
    }
  }

  initDots();

  let motionVector = { dx: 0, dy: 0, intensity: 0, ax: 0, ay: 0, az: 9.81 };
  let currentOffset = { x: 0, y: 0 };

  // Connect SSE (Server-Sent Events)
  let eventSource = null;
  function connectSSE() {
    eventSource = new EventSource('/events');
    eventSource.onopen = () => {
      statusDot.style.background = '#00ff88';
      statusDot.style.boxShadow = '0 0 8px #00ff88';
      statusText.textContent = 'ZOTAQUE CUES [LIVE]';
    };
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        motionVector = data;
        telemetry.innerHTML = `DX: ${(data.dx >= 0 ? '+' : '') + data.dx.toFixed(2)} | DY: ${(data.dy >= 0 ? '+' : '') + data.dy.toFixed(2)}<br>AX: ${data.ax} | AY: ${data.ay} | AZ: ${data.az}`;
      } catch (err) {}
    };
    eventSource.onerror = () => {
      statusDot.style.background = '#ffaa00';
      statusDot.style.boxShadow = '0 0 8px #ffaa00';
      statusText.textContent = 'RECONNECTING...';
    };
  }

  connectSSE();

  // Animation Loop
  function animate() {
    ctx.clearRect(0, 0, width, height);

    const targetX = motionVector.dx * config.max_shift_px;
    const targetY = motionVector.dy * config.max_shift_px;

    currentOffset.x += (targetX - currentOffset.x) * 0.15;
    currentOffset.y += (targetY - currentOffset.y) * 0.15;

    const alpha = 0.35 + (motionVector.intensity || 0) * 0.6;

    for (const dot of dots) {
      dot.x = dot.base_x + currentOffset.x;
      dot.y = dot.base_y + currentOffset.y;

      ctx.beginPath();
      ctx.arc(dot.x, dot.y, config.dot_radius, 0, Math.PI * 2);
      ctx.fillStyle = config.dot_color;
      ctx.globalAlpha = Math.min(1, alpha);
      ctx.shadowBlur = 10;
      ctx.shadowColor = config.dot_color;
      ctx.fill();
    }

    ctx.globalAlpha = 1.0;
    requestAnimationFrame(animate);
  }

  animate();
</script>
</body>
</html>
"""
