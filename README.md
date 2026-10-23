# Backyard Birds ➔ InkJoy Muse E-Ink Picture Frame

Automated bird identification and vintage naturalist field-guide art for your **InkJoy Muse** color E-ink picture frame, powered by **BirdNET-Go** and **Tesserae** on **Home Assistant Green**.

---

## 🏛️ Architecture

```
Camera RTSP Audio (stream_1)
        │
        ▼
BirdNET-Go App (Home Assistant Green)
  - 100% Local AI acoustic model (Cornell BirdNET v2.4)
  - Regional species filtering & noise suppression
        │
        ▼
Tesserae App (Home Assistant Green)
  - Backyard Birds widget
  - Natural history plates (Audubon, Gould, Lear)
  - 1200×1600 e-ink rendered layouts
        │
        ▼
InkJoy Bridge (Python / Home Assistant automation)
  - SHA-256 smart visual hash check (skips if unchanged)
  - Uploads to InkJoy OpenAPI (openapi.inkjoyframe.com)
        │
        ▼
InkJoy Muse 13.3" Frame (on your wall)
```

---

## 🚀 Setup Overview

### 1. Home Assistant Apps Installed
* **Birdnet-go** (from `alexbelgium/hassio-addons`): Audio source set to camera RTSP (`stream_1`).
* **Tesserae** (from `dmellok/homeassistant-tesserae-addon`): Port `8765` exposed under Configuration.
* **Mosquitto broker**: Providing MQTT discovery.

### 2. Configuration (`/config/.env`)
Create `/config/.env` in Home Assistant:
```env
INKJOY_EMAIL=your_email@example.com
INKJOY_PASSWORD=your_password
INKJOY_DEVICE_ID=04705c97-0151-45c0-b2d0-593f329bbdc5
TESSERAE_URL=http://homeassistant.local:8765
TESSERAE_TOKEN=your_mcp_token_from_tesserae
BIRDNET_URL=http://db21ed7f-birdnet-go:8080
BIRD_LAYOUT=cluster
BIRD_STYLE=sheet
```

### 3. Home Assistant `configuration.yaml`
Auto-pulls the latest bridge script from GitHub on every run:
```yaml
shell_command:
  push_bird_to_inkjoy: >-
    curl -fsSL https://raw.githubusercontent.com/borcherspm/birdnet-inkjoy/main/scripts/inkjoy_bridge.py -o /config/scripts/inkjoy_bridge.py && python3 /config/scripts/inkjoy_bridge.py --tesserae-render
```

### 4. 15-Minute Daytime Automation
In Home Assistant (`Settings → Automations`):
```yaml
alias: "Birds: 15-Minute Day Check"
description: "Pushes fresh bird artwork to InkJoy frame every 15 minutes during daylight hours"
trigger:
  - platform: time_pattern
    minutes: "/15"
condition:
  - condition: time
    after: "07:00:00"
    before: "18:00:00"
action:
  - action: shell_command.push_bird_to_inkjoy
mode: single
```

---

## 🔋 Battery Optimization (Smart Hash Check)
`scripts/inkjoy_bridge.py` computes a **SHA-256 fingerprint** of the rendered 1200×1600 artwork before sending:
* If no new birds were detected and the artwork is identical to the last push, it logs:
  `💤 Image is identical to last push. Skipping upload to preserve InkJoy battery.`
  and exits immediately without contacting the cloud or waking your frame.
* Only changes trigger an upload, giving you **months of battery life**!
