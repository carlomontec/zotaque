import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
  DropdownItem,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { VFC, useState, useEffect } from "react";
import { FaCar, FaSlidersH } from "react-icons/fa";

class InGameOverlayManager {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private eventSource: EventSource | null = null;
  private animFrameId: number | null = null;
  private pollIntervalId: any = null;
  public isRunning: boolean = false;

  public config = {
    tilt_sensitivity: 1.0,
    dynamic_sensitivity: 1.2,
    max_shift_px: 50,
    dot_radius: 7,
    dot_color: "#00e5ff",
    dot_count_edge: 8,
  };

  private motionVector = { dx: 0, dy: 0, intensity: 0 };
  private currentOffset = { x: 0, y: 0 };
  private dots: Array<{ base_x: number; base_y: number; x: number; y: number }> = [];

  private getRootDocument(): Document {
    try {
      if (window.opener && window.opener.document && window.opener.document.body) {
        return window.opener.document;
      }
      if (window.top && window.top.document && window.top.document.body) {
        return window.top.document;
      }
    } catch (e) {}
    return document;
  }

  public start() {
    if (this.isRunning) return;
    this.isRunning = true;

    const targetDoc = this.getRootDocument();
    let el = targetDoc.getElementById("zotaque-in-game-motion-cues") as HTMLCanvasElement;
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
    window.addEventListener("resize", this.resizeCanvas);

    // Connect SSE stream
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

  public stop() {
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
    window.removeEventListener("resize", this.resizeCanvas);
  }

  private resizeCanvas = () => {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.initDots();
  };

  private initDots() {
    this.dots = [];
    if (!this.canvas) return;
    const w = this.canvas.width || window.innerWidth;
    const h = this.canvas.height || window.innerHeight;
    const margin = 28;
    const count = this.config.dot_count_edge;

    // Top & Bottom
    for (let i = 0; i < count; i++) {
      const x = margin + ((w - margin * 2) / (count - 1)) * i;
      this.dots.push({ base_x: x, base_y: margin, x: x, y: margin });
      this.dots.push({ base_x: x, base_y: h - margin, x: x, y: h - margin });
    }
    // Left & Right
    for (let i = 1; i < count - 1; i++) {
      const y = margin + ((h - margin * 2) / (count - 1)) * i;
      this.dots.push({ base_x: margin, base_y: y, x: margin, y: y });
      this.dots.push({ base_x: w - margin, base_y: y, x: w - margin, y: y });
    }
  }

  private animate = () => {
    if (!this.isRunning || !this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    const targetX = (this.motionVector.dx || 0) * this.config.max_shift_px;
    const targetY = (this.motionVector.dy || 0) * this.config.max_shift_px;

    this.currentOffset.x += (targetX - this.currentOffset.x) * 0.15;
    this.currentOffset.y += (targetY - this.currentOffset.y) * 0.15;

    const alpha = 0.4 + (this.motionVector.intensity || 0) * 0.55;

    for (const dot of this.dots) {
      const x = dot.base_x + this.currentOffset.x;
      const y = dot.base_y + this.currentOffset.y;

      this.ctx.beginPath();
      this.ctx.arc(x, y, this.config.dot_radius, 0, Math.PI * 2);
      this.ctx.fillStyle = this.config.dot_color;
      this.ctx.globalAlpha = Math.min(1, alpha);
      this.ctx.shadowBlur = 10;
      this.ctx.shadowColor = this.config.dot_color;
      this.ctx.fill();
    }

    this.ctx.globalAlpha = 1.0;
    this.animFrameId = requestAnimationFrame(this.animate);
  };
}

// Global persistent singleton
const globalKey = "__zotaque_overlay_mgr";
if (!(window as any)[globalKey]) {
  (window as any)[globalKey] = new InGameOverlayManager();
}
const overlayManager: InGameOverlayManager = (window as any)[globalKey];

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const [inGameEnabled, setInGameEnabled] = useState<boolean>(overlayManager.isRunning);
  const [tiltSens, setTiltSens] = useState<number>(overlayManager.config.tilt_sensitivity);
  const [dotColor, setDotColor] = useState<string>(overlayManager.config.dot_color);
  const [rgbMode, setRgbMode] = useState<string>("rainbow");
  const [brightness, setBrightness] = useState<number>(80);
  const [apuTemp, setApuTemp] = useState<number | null>(null);

  useEffect(() => {
    // Single fetch on panel open
    serverAPI.callPluginMethod<{}, { temperature: number }>("get_apu_temperature", {})
      .then((res) => {
        if (res.success && res.result && res.result.temperature) {
          setApuTemp(res.result.temperature);
        }
      })
      .catch(() => {});
  }, []);

  const toggleMotionCues = (checked: boolean) => {
    setInGameEnabled(checked);
    if (checked) {
      overlayManager.start();
    } else {
      overlayManager.stop();
    }
  };

  const updateRgb = (mode: string, b: number) => {
    serverAPI.callPluginMethod("set_rgb_mode", {
      mode,
      hex_color: "00e5ff",
      brightness: b,
      speed: 5,
    }).catch(() => {});
  };

  return (
    <PanelSection title="Zotaque Controls">
      {apuTemp !== null && (
        <PanelSectionRow>
          <div>APU Temp: {apuTemp.toFixed(1)}°C</div>
        </PanelSectionRow>
      )}

      <PanelSection title="Vehicle Motion Cues">
        <PanelSectionRow>
          <ToggleField
            label="In-Game Motion Cues"
            description="Draw kinetic dots over games to reduce motion sickness"
            checked={inGameEnabled}
            onChange={toggleMotionCues}
          />
        </PanelSectionRow>

        <PanelSectionRow>
          <SliderField
            label="Tilt Sensitivity"
            value={tiltSens}
            min={0}
            max={3}
            step={0.1}
            onChange={(val) => {
              setTiltSens(val);
              overlayManager.config.tilt_sensitivity = val;
            }}
          />
        </PanelSectionRow>

        <PanelSectionRow>
          <DropdownItem
            label="Dot Color"
            rgOptions={[
              { data: "#00e5ff", label: "Neon Cyan" },
              { data: "#00ff88", label: "Emerald Green" },
              { data: "#ff007f", label: "Neon Pink" },
              { data: "#ffaa00", label: "Amber Orange" },
              { data: "#ffffff", label: "Pure White" },
            ]}
            selectedOption={dotColor}
            onChange={(opt) => {
              setDotColor(opt.data);
              overlayManager.config.dot_color = opt.data;
            }}
          />
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="RGB Lighting">
        <PanelSectionRow>
          <DropdownItem
            label="Halo Rings Mode"
            rgOptions={[
              { data: "rainbow", label: "Rainbow Wave" },
              { data: "static", label: "Static Teal" },
              { data: "breathing", label: "Breathing" },
              { data: "off", label: "Disabled" },
            ]}
            selectedOption={rgbMode}
            onChange={(opt) => {
              setRgbMode(opt.data);
              updateRgb(opt.data, brightness);
            }}
          />
        </PanelSectionRow>

        <PanelSectionRow>
          <SliderField
            label="Brightness"
            value={brightness}
            min={0}
            max={100}
            step={5}
            onChange={(val) => {
              setBrightness(val);
              updateRgb(rgbMode, val);
            }}
          />
        </PanelSectionRow>
      </PanelSection>
    </PanelSection>
  );
};

export default definePlugin((serverAPI: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>Zotaque</div>,
    content: <Content serverAPI={serverAPI} />,
    icon: <FaCar />,
    onDismount() {},
  };
});
