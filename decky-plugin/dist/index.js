(function () {
  'use strict';

  var React = window.SP_REACT || window.React;
  var DFL = window.DFL || {};

  // Global In-Game Overlay Manager
  function InGameOverlayManager() {
    this.canvas = null;
    this.ctx = null;
    this.animFrameId = null;
    this.serverAPI = null;
    this.hookListener = null;
    this.pollTimer = null;
    this.isRunning = false;
    this.config = {
      tilt_sensitivity: 1.0,
      dynamic_sensitivity: 1.2,
      max_shift_px: 50,
      dot_radius: 7,
      dot_color: "#00e5ff",
      dot_count_edge: 8
    };
    this.motionVector = { dx: 0, dy: 0, intensity: 0 };
    this.currentOffset = { x: 0, y: 0 };
    this.dots = [];
  }

  InGameOverlayManager.prototype.getRootDocument = function () {
    try {
      if (window.opener && window.opener.document && window.opener.document.body) {
        return window.opener.document;
      }
      if (window.top && window.top.document && window.top.document.body) {
        return window.top.document;
      }
    } catch (e) {}
    return document;
  };

  InGameOverlayManager.prototype.start = function (serverAPI) {
    if (this.isRunning) return;
    this.isRunning = true;
    this.serverAPI = serverAPI;

    var targetDoc = this.getRootDocument();
    var el = targetDoc.getElementById("zotaque-in-game-motion-cues");
    if (!el) {
      el = targetDoc.createElement("canvas");
      el.id = "zotaque-in-game-motion-cues";
      el.style.position = "fixed";
      el.style.top = "0";
      el.style.left = "0";
      el.style.width = "100vw";
      el.style.height = "100vh";
      el.style.pointerEvents = "none";
      el.style.zIndex = "999999";
      el.style.background = "transparent";
      targetDoc.body.appendChild(el);
    }
    this.canvas = el;
    this.ctx = this.canvas.getContext("2d");

    this.resizeCanvas();
    var self = this;
    this._onResize = function () { self.resizeCanvas(); };
    window.addEventListener("resize", this._onResize);

    // 1. Hook native Decky router event
    if (serverAPI && serverAPI.router && serverAPI.router.hook) {
      try {
        this.hookListener = serverAPI.router.hook("zotaque_motion", function (data) {
          if (data) self.motionVector = data;
        });
      } catch (err) {}
    }

    // 2. High-speed fallback poll via direct plugin method
    if (serverAPI && serverAPI.callPluginMethod) {
      this.pollTimer = setInterval(function () {
        serverAPI.callPluginMethod("get_motion_sample", {})
          .then(function (res) {
            if (res && res.success && res.result) {
              self.motionVector = res.result;
            }
          })
          .catch(function () {});
      }, 50); // 20 Hz fallback
    }

    this.animate();
  };

  InGameOverlayManager.prototype.stop = function () {
    this.isRunning = false;
    if (this.hookListener && this.hookListener.unregister) {
      try { this.hookListener.unregister(); } catch (e) {}
      this.hookListener = null;
    }
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
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
  };

  InGameOverlayManager.prototype.resizeCanvas = function () {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.initDots();
  };

  InGameOverlayManager.prototype.initDots = function () {
    this.dots = [];
    if (!this.canvas) return;
    var w = this.canvas.width || window.innerWidth;
    var h = this.canvas.height || window.innerHeight;
    var margin = 28;
    var count = this.config.dot_count_edge;

    for (var i = 0; i < count; i++) {
      var x = margin + ((w - margin * 2) / (count - 1)) * i;
      this.dots.push({ base_x: x, base_y: margin });
      this.dots.push({ base_x: x, base_y: h - margin });
    }
    for (var j = 1; j < count - 1; j++) {
      var y = margin + ((h - margin * 2) / (count - 1)) * j;
      this.dots.push({ base_x: margin, base_y: y });
      this.dots.push({ base_x: w - margin, base_y: y });
    }
  };

  InGameOverlayManager.prototype.animate = function () {
    if (!this.isRunning || !this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    var targetX = (this.motionVector.dx || 0) * this.config.max_shift_px;
    var targetY = (this.motionVector.dy || 0) * this.config.max_shift_px;

    this.currentOffset.x += (targetX - this.currentOffset.x) * 0.15;
    this.currentOffset.y += (targetY - this.currentOffset.y) * 0.15;

    var alpha = 0.4 + (this.motionVector.intensity || 0) * 0.55;

    for (var i = 0; i < this.dots.length; i++) {
      var dot = this.dots[i];
      var dotX = dot.base_x + this.currentOffset.x;
      var dotY = dot.base_y + this.currentOffset.y;

      this.ctx.beginPath();
      this.ctx.arc(dotX, dotY, this.config.dot_radius, 0, Math.PI * 2);
      this.ctx.fillStyle = this.config.dot_color;
      this.ctx.globalAlpha = Math.min(1, alpha);
      this.ctx.shadowBlur = 10;
      this.ctx.shadowColor = this.config.dot_color;
      this.ctx.fill();
    }

    this.ctx.globalAlpha = 1.0;
    var self = this;
    this.animFrameId = requestAnimationFrame(function () { self.animate(); });
  };

  if (!window.__zotaque_overlay_mgr) {
    window.__zotaque_overlay_mgr = new InGameOverlayManager();
  }
  var overlay = window.__zotaque_overlay_mgr;

  // React Component with native Steam gamepad navigation
  function ZotaquePanel(props) {
    var serverAPI = props.serverAPI;
    var _a = React.useState(overlay.isRunning), inGameEnabled = _a[0], setInGameEnabled = _a[1];
    var _b = React.useState(overlay.config.tilt_sensitivity), tiltSens = _b[0], setTiltSens = _b[1];
    var _c = React.useState(overlay.config.dot_color), dotColor = _c[0], setDotColor = _c[1];
    var _d = React.useState(null), apuTemp = _d[0], setApuTemp = _d[1];

    React.useEffect(function () {
      if (serverAPI && serverAPI.callPluginMethod) {
        serverAPI.callPluginMethod("get_apu_temperature", {})
          .then(function (res) {
            if (res && res.success && res.result && res.result.temperature) {
              setApuTemp(res.result.temperature);
            }
          })
          .catch(function () {});
      }
    }, []);

    var toggleMotionCues = function (checked) {
      setInGameEnabled(checked);
      if (checked) overlay.start(serverAPI);
      else overlay.stop();
    };

    var PanelSection = DFL.PanelSection || 'div';
    var PanelSectionRow = DFL.PanelSectionRow || 'div';
    var ToggleField = DFL.ToggleField;
    var SliderField = DFL.SliderField;
    var DropdownItem = DFL.DropdownItem;

    var colorOptions = [
      { data: "#00e5ff", label: "Neon Cyan" },
      { data: "#00ff88", label: "Emerald Green" },
      { data: "#ff007f", label: "Neon Pink" },
      { data: "#ffaa00", label: "Amber Orange" },
      { data: "#ffffff", label: "Pure White" }
    ];

    return React.createElement(
      PanelSection,
      { title: "Zotaque Companion Suite" },
      apuTemp !== null && React.createElement(
        PanelSectionRow,
        null,
        React.createElement("div", { style: { opacity: 0.9 } }, "APU Temperature: " + apuTemp.toFixed(1) + "\u00B0C")
      ),
      React.createElement(
        PanelSection,
        { title: "Vehicle Motion Cues" },
        ToggleField ? React.createElement(
          PanelSectionRow,
          null,
          React.createElement(ToggleField, {
            label: "In-Game Motion Cues",
            description: "Draw kinetic dots over games to reduce motion sickness",
            checked: inGameEnabled,
            onChange: toggleMotionCues
          })
        ) : null,
        SliderField ? React.createElement(
          PanelSectionRow,
          null,
          React.createElement(SliderField, {
            label: "Tilt Sensitivity",
            value: tiltSens,
            min: 0,
            max: 3,
            step: 0.1,
            onChange: function (val) {
              setTiltSens(val);
              overlay.config.tilt_sensitivity = val;
              if (serverAPI && serverAPI.callPluginMethod) {
                serverAPI.callPluginMethod("update_motion_config", { tilt_sensitivity: val });
              }
            }
          })
        ) : null,
        DropdownItem ? React.createElement(
          PanelSectionRow,
          null,
          React.createElement(DropdownItem, {
            label: "Dot Accent Color",
            rgOptions: colorOptions,
            selectedOption: dotColor,
            onChange: function (opt) {
              var val = opt.data || opt;
              setDotColor(val);
              overlay.config.dot_color = val;
            }
          })
        ) : null
      )
    );
  }

  function definePlugin(serverAPI) {
    var TitleClass = (DFL.staticClasses && DFL.staticClasses.Title) || "";
    return {
      title: React.createElement("div", { className: TitleClass }, "Zotaque"),
      content: React.createElement(ZotaquePanel, { serverAPI: serverAPI }),
      icon: React.createElement("span", null, "🚗"),
      onDismount: function () {
        overlay.stop();
      }
    };
  }

  if (typeof window !== "undefined") {
    window.definePlugin = definePlugin;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = definePlugin;
  }
  return definePlugin;

})();
