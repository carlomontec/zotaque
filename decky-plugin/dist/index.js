(function () {
  'use strict';

  var React = window.SP_REACT || window.React;
  var DFL = window.DFL || {};

  function ZotaquePanel(props) {
    var serverAPI = props.serverAPI;
    var _a = React.useState(true), inGameEnabled = _a[0], setInGameEnabled = _a[1];
    var _b = React.useState(1.0), tiltSens = _b[0], setTiltSens = _b[1];
    var _c = React.useState("#00e5ff"), dotColor = _c[0], setDotColor = _c[1];

    React.useEffect(function () {
      if (serverAPI && serverAPI.callPluginMethod) {
        serverAPI.callPluginMethod("get_overlay_status", {})
          .then(function (res) {
            if (res && res.success && res.result && typeof res.result.enabled === "boolean") {
              setInGameEnabled(res.result.enabled);
            }
          })
          .catch(function () {});
      }
    }, []);

    var toggleMotionCues = function (checked) {
      setInGameEnabled(checked);
      if (serverAPI && serverAPI.callPluginMethod) {
        serverAPI.callPluginMethod("toggle_motion_cues", { enabled: checked }).catch(function () {});
      }
    };

    var updateConfig = function (sens, color) {
      if (serverAPI && serverAPI.callPluginMethod) {
        serverAPI.callPluginMethod("update_motion_config", {
          tilt_sensitivity: sens,
          dot_color_hex: color
        }).catch(function () {});
      }
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
      { title: "Zotaque Motion Cues" },
      ToggleField ? React.createElement(
        PanelSectionRow,
        null,
        React.createElement(ToggleField, {
          label: "In-Game Motion Cues",
          description: "Native 120Hz overlay to relieve motion sickness in vehicles",
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
            updateConfig(val, dotColor);
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
            updateConfig(tiltSens, val);
          }
        })
      ) : null
    );
  }

  function definePlugin(serverAPI) {
    var TitleClass = (DFL.staticClasses && DFL.staticClasses.Title) || "";
    return {
      title: React.createElement("div", { className: TitleClass }, "Zotaque"),
      content: React.createElement(ZotaquePanel, { serverAPI: serverAPI }),
      icon: React.createElement("span", null, "🚗"),
      onDismount: function () {}
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
