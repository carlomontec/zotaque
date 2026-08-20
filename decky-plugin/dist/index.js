(function (React) {
  'use strict';

  class InGameOverlayManager {
    constructor() {
      this.canvas = null;
      this.ctx = null;
      this.eventSource = null;
      this.animFrameId = null;
      this.isRunning = false;
      this.config = {
        tilt_sensitivity: 1.0,
        dynamic_sensitivity: 1.2,
        max_shift_px: 45,
        dot_radius: 6,
        dot_color: "#00e5ff",
        dot_count_edge: 8
      };
      this.motionVector = { dx: 0, dy: 0, intensity: 0 };
      this.currentOffset = { x: 0, y: 0 };
      this.dots = [];
    }

    start() {
      if (this.isRunning) return;
      this.isRunning = true;

      // Create transparent viewport overlay canvas
      let el = document.getElementById("zotaque-in-game-motion-cues");
      if (!el) {
        el = document.createElement("canvas");
        el.id = "zotaque-in-game-motion-cues";
        el.style.position = "fixed";
        el.style.top = "0";
        el.style.left = "0";
        el.style.width = "100vw";
        el.style.height = "100vh";
        el.style.pointerEvents = "none";
        el.style.zIndex = "999999";
        el.style.background = "transparent";
        document.body.appendChild(el);
      }
      this.canvas = el;
      this.ctx = this.canvas.getContext("2d");

      this.resizeCanvas();
      this._onResize = () => this.resizeCanvas();
      window.addEventListener("resize", this._onResize);

      try {
        if (this.eventSource) this.eventSource.close();
        this.eventSource = new EventSource("http://127.0.0.1:8765/events");
        this.eventSource.onmessage = (e) => {
          try {
            this.motionVector = JSON.parse(e.data);
          } catch (err) {}
        };
      } catch (err) {}

      this.animate();
    }

    stop() {
      this.isRunning = false;
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
        this.animFrameId = null;
      }
      if (this.canvas) {
        if (this.ctx) this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        if (this.canvas.parentNode) {
          this.canvas.parentNode.removeChild(this.canvas);
        }
        this.canvas = null;
        this.ctx = null;
      }
      if (this._onResize) {
        window.removeEventListener("resize", this._onResize);
      }
    }

    resizeCanvas() {
      if (!this.canvas) return;
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
      this.initDots();
    }

    initDots() {
      this.dots = [];
      if (!this.canvas) return;
      const w = this.canvas.width;
      const h = this.canvas.height;
      const margin = 28;
      const count = this.config.dot_count_edge;

      for (let i = 0; i < count; i++) {
        const x = margin + ((w - margin * 2) / (count - 1)) * i;
        this.dots.push({ base_x: x, base_y: margin });
        this.dots.push({ base_x: x, base_y: h - margin });
      }
      for (let i = 1; i < count - 1; i++) {
        const y = margin + ((h - margin * 2) / (count - 1)) * i;
        this.dots.push({ base_x: margin, base_y: y });
        this.dots.push({ base_x: w - margin, base_y: y });
      }
    }

    animate() {
      if (!this.isRunning || !this.ctx || !this.canvas) return;

      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      const targetX = this.motionVector.dx * this.config.max_shift_px;
      const targetY = this.motionVector.dy * this.config.max_shift_px;

      this.currentOffset.x += (targetX - this.currentOffset.x) * 0.15;
      this.currentOffset.y += (targetY - this.currentOffset.y) * 0.15;

      const alpha = 0.35 + (this.motionVector.intensity || 0) * 0.6;

      for (const dot of this.dots) {
        const x = dot.base_x + this.currentOffset.x;
        const y = dot.base_y + this.currentOffset.y;

        this.ctx.beginPath();
        this.ctx.arc(x, y, this.config.dot_radius, 0, Math.PI * 2);
        this.ctx.fillStyle = this.config.dot_color;
        this.ctx.globalAlpha = Math.min(1, alpha);
        this.ctx.shadowBlur = 8;
        this.ctx.shadowColor = this.config.dot_color;
        this.ctx.fill();
      }

      this.ctx.globalAlpha = 1.0;
      this.animFrameId = requestAnimationFrame(() => this.animate());
    }
  }

  // Singleton overlay instance
  if (!window.__zotaque_overlay) {
    window.__zotaque_overlay = new InGameOverlayManager();
  }
  const overlay = window.__zotaque_overlay;

  function ZotaquePanel({ serverAPI }) {
    const [enabled, setEnabled] = React.useState(overlay.isRunning);
    const [tiltSens, setTiltSens] = React.useState(overlay.config.tilt_sensitivity);
    const [dotColor, setDotColor] = React.useState(overlay.config.dot_color);

    const toggleCues = (val) => {
      setEnabled(val);
      if (val) overlay.start();
      else overlay.stop();
    };

    return React.createElement(
      "div",
      { style: { padding: "8px", color: "#fff", display: "flex", flexDirection: "column", gap: "12px" } },
      React.createElement(
        "div",
        { style: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.15)" } },
        React.createElement("span", { style: { fontWeight: "bold", color: "#00e5ff" } }, "In-Game Motion Cues"),
        React.createElement("input", {
          type: "checkbox",
          checked: enabled,
          onChange: (e) => toggleCues(e.target.checked),
          style: { width: "22px", height: "22px", cursor: "pointer" }
        })
      ),
      React.createElement(
        "div",
        null,
        React.createElement("div", { style: { fontSize: "12px", marginBottom: "4px" } }, `Tilt Sensitivity: ${tiltSens}`),
        React.createElement("input", {
          type: "range",
          min: "0",
          max: "3",
          step: "0.1",
          value: tiltSens,
          onChange: (e) => {
            const v = parseFloat(e.target.value);
            setTiltSens(v);
            overlay.config.tilt_sensitivity = v;
          },
          style: { width: "100%" }
        })
      ),
      React.createElement(
        "div",
        null,
        React.createElement("div", { style: { fontSize: "12px", marginBottom: "4px" } }, "Dot Accent Color"),
        React.createElement(
          "select",
          {
            value: dotColor,
            onChange: (e) => {
              setDotColor(e.target.value);
              overlay.config.dot_color = e.target.value;
            },
            style: { width: "100%", padding: "6px", background: "#1e293b", color: "#fff", border: "1px solid #334155", borderRadius: "6px" }
          },
          React.createElement("option", { value: "#00e5ff" }, "Neon Cyan"),
          React.createElement("option", { value: "#00ff88" }, "Emerald Green"),
          React.createElement("option", { value: "#ff007f" }, "Neon Pink"),
          React.createElement("option", { value: "#ffaa00" }, "Amber Orange"),
          React.createElement("option", { value: "#ffffff" }, "Pure White")
        )
      )
    );
  }

  function definePlugin(serverAPI) {
    return {
      title: React.createElement("div", null, "Zotaque"),
      content: React.createElement(ZotaquePanel, { serverAPI: serverAPI }),
      icon: React.createElement("span", null, "🚗"),
      onDismount() {}
    };
  }

  if (typeof window !== "undefined") {
    window.definePlugin = definePlugin;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = definePlugin;
  }
  return definePlugin;

})(window.SP_REACT || window.React);
