"""
Standalone HTML/CSS/Canvas overlay replicating Apple Vehicle Motion Cues.
Renders kinetic floating dots along screen boundaries synced via WebSocket.
"""

OVERLAY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zotaque Motion Cues Overlay</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body, html {
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: transparent;
    pointer-events: none;
    user-select: none;
  }
  #motionCanvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    display: block;
  }
  #hud {
    position: absolute;
    bottom: 12px;
    right: 12px;
    background: rgba(0, 0, 0, 0.4);
    color: #00e5ff;
    font-family: monospace;
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 4px;
    opacity: 0.7;
  }
</style>
</head>
<body>
<canvas id="motionCanvas"></canvas>
<div id="hud">ZOTAQUE CUES [DISCONNECTED]</div>

<script>
  const canvas = document.getElementById('motionCanvas');
  const ctx = canvas.getContext('2d');
  const hud = document.getElementById('hud');

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

  let motionVector = { dx: 0, dy: 0, intensity: 0 };
  let currentOffset = { x: 0, y: 0 };
  const dots = [];
  const DOT_COUNT_PER_EDGE = 7;
  const BASE_DOT_RADIUS = 5;

  function initDots() {
    dots.length = 0;
    const margin = 32;

    // Top & Bottom Edge Dots
    for (let i = 0; i < DOT_COUNT_PER_EDGE; i++) {
      const x = margin + ((width - margin * 2) / (DOT_COUNT_PER_EDGE - 1)) * i;
      dots.push({ base_x: x, base_y: margin, x: x, y: margin, edge: 'top' });
      dots.push({ base_x: x, base_y: height - margin, x: x, y: height - margin, edge: 'bottom' });
    }

    // Left & Right Edge Dots
    for (let i = 1; i < DOT_COUNT_PER_EDGE - 1; i++) {
      const y = margin + ((height - margin * 2) / (DOT_COUNT_PER_EDGE - 1)) * i;
      dots.push({ base_x: margin, base_y: y, x: margin, y: y, edge: 'left' });
      dots.push({ base_x: width - margin, base_y: y, x: width - margin, y: y, edge: 'right' });
    }
  }

  initDots();

  // Connect WebSocket
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  let socket;

  function connectWS() {
    socket = new WebSocket(wsUrl);
    socket.onopen = () => {
      hud.textContent = "ZOTAQUE CUES [LIVE]";
      hud.style.color = "#00ff88";
    };
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        motionVector.dx = data.dx || 0;
        motionVector.dy = data.dy || 0;
        motionVector.intensity = data.intensity || 0;
      } catch (e) {}
    };
    socket.onclose = () => {
      hud.textContent = "ZOTAQUE CUES [RECONNECTING]";
      hud.style.color = "#ffaa00";
      setTimeout(connectWS, 1500);
    };
  }

  connectWS();

  // Animation Loop
  function animate() {
    ctx.clearRect(0, 0, width, height);

    // Smooth lerp offset
    const maxShift = 45; // Max pixel shift
    const targetX = motionVector.dx * maxShift;
    const targetY = motionVector.dy * maxShift;

    currentOffset.x += (targetX - currentOffset.x) * 0.12;
    currentOffset.y += (targetY - currentOffset.y) * 0.12;

    const baseAlpha = 0.4 + motionVector.intensity * 0.55;

    for (const dot of dots) {
      dot.x = dot.base_x + currentOffset.x;
      dot.y = dot.base_y + currentOffset.y;

      ctx.beginPath();
      ctx.arc(dot.x, dot.y, BASE_DOT_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 229, 255, ${baseAlpha.toFixed(2)})`;
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(0, 229, 255, 0.6)';
      ctx.fill();
    }

    requestAnimationFrame(animate);
  }

  animate();
</script>
</body>
</html>
"""
