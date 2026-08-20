import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  SliderField,
  DropdownItem,
  ButtonItem,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { VFC, useState, useEffect } from "react";
import { FaSlidersH, FaLightbulb, FaCar } from "react-icons/fa";

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const [rgbMode, setRgbMode] = useState<string>("rainbow");
  const [brightness, setBrightness] = useState<number>(80);
  const [apuTemp, setApuTemp] = useState<number | null>(null);

  useEffect(() => {
    const fetchTemp = async () => {
      const res = await serverAPI.callPluginMethod<{}, { temperature: number }>("get_apu_temperature", {});
      if (res.success && res.result.temperature) {
        setApuTemp(res.result.temperature);
      }
    };
    fetchTemp();
    const interval = setInterval(fetchTemp, 3000);
    return () => clearInterval(interval);
  }, []);

  const updateRgb = async (mode: string, b: number) => {
    await serverAPI.callPluginMethod("set_rgb_mode", {
      mode,
      hex_color: "00e5ff",
      brightness: b,
      speed: 5
    });
  };

  return (
    <PanelSection title="Zotaque Controls">
      <PanelSectionRow>
        <div>APU Temperature: {apuTemp !== null ? `${apuTemp.toFixed(1)}°C` : "Reading..."}</div>
      </PanelSectionRow>

      <PanelSection title="RGB Lighting">
        <PanelSectionRow>
          <DropdownItem
            label="Lighting Mode"
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

      <PanelSection title="Vehicle Motion Cues">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              window.open("http://127.0.0.1:8765", "_blank");
            }}
          >
            Launch Motion Cues Overlay
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </PanelSection>
  );
};

export default definePlugin((serverAPI: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>Zotaque</div>,
    content: <Content serverAPI={serverAPI} />,
    icon: <FaSlidersH />,
    onDismount() {},
  };
});
