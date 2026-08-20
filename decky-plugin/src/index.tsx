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
import { VFC, useState, useEffect, useRef } from "react";
import { FaCar, FaSlidersH, FaLightbulb, FaThermometerHalf } from "react-icons/fa";

// Global overlay controller to keep canvas rendering even when QAM panel is closed
class InGameOverlayManager {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private eventSource: EventSource | null = null;
  private animFrameId: number | null = null;
  public isRunning: boolean = false;

  public config = {
    tilt_sensitivity: 1.0,
    dynamic_sensitivity: 1.2,
    smoothing: 0.85,
    max_shift_px: 50,
    dot_radius: 6,
    dot_color: "#00e5ff",
    dot_count_edge: 8,
  };

  private motionVector = { dx: 0, dy: 0, intensity: 0 };
  private currentOffset = { x: 0, y: 0 };
  private dots: Array<{ base_x: number; base_y: number; x: number; y: number }> = [];

  public start() {
    if (this.isRunning) return;
    this.isRunning = true;

    // Create and attach global canvas directly to Steam root document body
    this.canvas = document.createElement("canvas");
    this.canvas.id = "zotaque-in-game-motion-cues";
    this.canvas.style.position = "fixed";
    this.canvas.style.top = "0";
    this.canvas.style.left = "0";
    this.canvas.style.width = "100vw";
    this.canvas.style.height = "100vh";
    this.canvas.style.pointerEvents = "none"; // Pass all clicks and gamepad inputs to the game
    this.canvas.style.zIndex = "999999";
    this.canvas.style.background = "transparent";
    document.body.appendChild(this.canvas);

    this.ctx = this.canvas.getContext("2d");
    this.resizeCanvas();
    window.addEventListener("resize", this.resizeCanvas);

    // Connect to Zotaque SSE stream
    this.eventSource = new EventSource("http://127.0.0.1:8765/events");
    this.eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.motionVector = data;
      } catch (err) {}
    };

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
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
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
    const w = this.canvas.width;
    const h = this.canvas.height;
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
      this.dots.push({ base_x: w - margin, base_y: y, x: width - margin, y: y });
    }
  }

  private animate = () => {
    if (!this.isRunning || !this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    const targetX = this.motionVector.dx * this.config.max_shift_px;
    const targetY = this.motionVector.dy * this.config.max_shift_px;

    this.currentOffset.x += (targetX - this.currentOffset.x) * 0.15;
    this.currentOffset.y += (targetY - this.currentOffset.y) * 0.15;

    const alpha = 0.35 + (this.motionVector.intensity || 0) * 0.6;

    for (const dot of this.dots) {
      dot.x = dot.base_x + this.currentOffset.x;
      dot.y = dot.base_y + this.currentOffset.y;

      this.ctx.beginPath();
      this.ctx.arc(dot.x, dot.y, this.config.dot_radius, 0, Math.PI * 2);
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

const overlayManager = new InGameOverlayManager();

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const [inGameCuesEnabled, setInGameCuesEnabled] = useState<boolean>(overlayManager.isRunning);
  const [dotColor, setDotColor] = useState<string>(overlayManager.config.dot_color);
  const [tiltSens, setTiltSens] = useState<number>(overlayManager.config.tilt_sensitivity);
  const [rgbMode, setRgbMode] = useState<string>("rainbow");
  const [brightness, setBrightness] = useState<number>(80);
  const [apuTemp, setApuTemp] = useState<number | null>(null);

  useEffect(() => {
    const fetchTemp = async () => {
      const res = await serverAPI.callPluginMethod<{}, { temperature: number }>("get_apu_temperature", {});
      if (res.success && res.result && res.result.temperature) {
        setApuTemp(res.result.temperature);
      }
    };
    fetchTemp();
    const interval = setInterval(fetchTemp, 3000);
    return () => clearInterval(interval);
  }, []);

  const toggleInGameCues = (enabled: boolean) => {
    setInGameCuesEnabled(enabled);
    if (enabled) {
      overlayManager.start();
    } else {
      overlayManager.stop();
    }
  };

  const updateRgb = async (mode: string, b: number) => {
    await serverAPI.callPluginMethod("set_rgb_mode", {
      mode,
      hex_color: "00e5ff",
      brightness: b,
      speed: 5,
    });
  };

  return (
    <PanelSection title="Zotaque Handheld Suite">
      <PanelSectionRow>
        <div>
          <FaThermometerHalf style={{ marginRight: 6, verticalAlign: "middle" }} />
          APU Temp: {apuTemp !== null ? `${apuTemp.toFixed(1)}°C` : "Reading..."}
        </div>
      </PanelSectionRow>

      <PanelSection title="Vehicle Motion Cues (In-Game)">
        <PanelSectionRow>
          <ToggleField
            label="In-Game Motion Cues"
            description="Draw floating anti-motion-sickness cues over running games"
            checked={inGameCuesEnabled}
            onChange={toggleInGameCues}
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
            label="Dot Accent Color"
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

      <PanelSection title="RGB Stick Lighting">
        <PanelSectionRow>
          <DropdownItem
            label="Halo Ring Mode"
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
    onDismount() {
      overlayManager.stop();
    },
  };
});
