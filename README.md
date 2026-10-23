# Backyard Bird Detection & E-Ink Dashboard

Turn your existing outdoor security cameras with microphones into an automated, 100% local backyard bird identification station and natural-history dashboard.

Based on the [Reddit Home Assistant project](https://www.reddit.com/r/homeassistant/comments/1x4k946/i_turned_my_security_cameras_into_a_backyard_bird/) by [@dmellok](https://github.com/dmellok) and the [Birding with AI runbook](https://github.com/mrebbert/Birding-with-AI).

---

## 🏛️ Architecture & How It Works

```
┌─────────────────────────────────┐
│ Security Camera(s)              │
│ (Hikvision, Reolink, UniFi,...) │
└────────────────┬────────────────┘
                 │ RTSP Audio Stream (TCP)
                 ▼
┌─────────────────────────────────┐
│ BirdNET-Go (Docker Container)   │
│ - 100% Local AI Model Inference │
│ - Cornell Lab BirdNET v2.4      │
│ - Range filter (Lat/Long)       │
│ - Real-time acoustic detection  │
└───────┬─────────────────┬───────┘
        │ REST API        │ MQTT Discovery
        ▼                 ▼
┌─────────────────┐ ┌─────────────────────────┐
│ Tesserae        │ │ Home Assistant          │
│ (E-Ink / Web)   │ │ - Triggered sensors     │
│ - Backyard Birds│ │ - Today/Total counters  │
│ - Classic Plates│ │ - Push notifications    │
│ - AI Paintings  │ │ - Mushroom / ApexCharts │
└─────────────────┘ └─────────────────────────┘
```

1. **Audio Capture**: Your security camera streams audio over local RTSP (`rtsp://...`).
2. **Local Machine Learning**: **BirdNET-Go** continuously analyzes the audio using Cornell's BirdNET acoustic neural network. Detections are filtered by your geographic coordinates (range filter) so only birds physically possible in your region are matched. Zero audio leaves your local network.
3. **Home Assistant**: Detections arrive via MQTT to provide real-time sensors, counters, hourly charts, and mobile push notifications when a new species is heard.
4. **Visual Art & Displays**:
   - **Tesserae**: Pulls from the BirdNET-Go API and renders antique natural-history folio plates (Audubon, Gould, Lear), specimen sheets, cyanotypes, or AI-generated paintings to e-ink frames (reTerminal, XIAO EE02, Inky Impression, Kindle) or any web browser.
   - **Saezuri / HABirdDashboard**: Generates an illustrated grid collage of recently heard birds.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- One or more IP security cameras with a microphone supporting RTSP (Hikvision, HiLook, Reolink, UniFi, Tapo, Amcrest, etc.).
- A machine running Docker & Docker Compose (Raspberry Pi 4/5, home server, NAS, or mini PC).

### 2. Camera Configuration
1. **Microphone gain**: Set the camera microphone sensitivity to **100%** in the camera's web UI. Bird calls need maximum pre-compression gain.
2. **Noise suppression**: **Disable** software noise suppression or speech enhancements on the camera. These algorithms filter out high frequencies where birds sing!
3. **Find your RTSP URL**:
   - *Hikvision / HiLook*: `rtsp://<user>:<password>@<ip>:554/Streaming/Channels/101`
   - *Reolink*: `rtsp://<user>:<password>@<ip>:554/h264Preview_01_main`
   - *UniFi Protect*: Enable RTSP on high quality (`rtsp://<gateway-ip>:7447/<token>`)
   - *Tapo*: `rtsp://<user>:<password>@<ip>:554/stream1`

Test your stream before launching:
```bash
cp .env.example .env
# Edit CAMERA_RTSP_URL in .env, then run:
./scripts/test_rtsp_stream.sh
```

---

### 3. Deploy the Stack with Docker Compose

Configure your `.env` file:
```bash
nano .env
```
Fill in your **latitude/longitude**, timezone, and RTSP stream.

Start the containers:
```bash
docker compose up -d
```
*(If you need a local Mosquitto MQTT broker, run `docker compose --profile with-mqtt up -d`)*

Container ports:
- **BirdNET-Go Web UI**: `http://<server-ip>:8080`
- **Tesserae Dashboard**: `http://<server-ip>:8765`
- **Saezuri Collage**: `http://<server-ip>:8090`

---

### 4. Configure BirdNET-Go

Open `http://<server-ip>:8080` in your browser:

1. **Security**: Set an administrative password under **Settings → Security**.
2. **Location**: Set **Latitude** and **Longitude** under **Settings → Node & Location**. This activates the range filter to avoid false positives from other continents.
3. **Audio Source**:
   - Add your RTSP URL (`rtsp://...`)
   - Select **Transport: TCP** (crucial for zero packet loss)
   - Enable **Equalizer** (150 Hz high-pass to filter road rumble)
   - Enable **Privacy Filter** (drops audio segments containing human voices)
4. **Detection Thresholds**:
   - Recommended start: **Confidence Threshold: 0.8**, **Overlap: 1.5**
   - For deep detection (requires 10 consecutive detections before reporting): **Threshold: 0.5**, **Overlap: 2.7**
5. **MQTT Integration (for Home Assistant)**:
   - Go to **Settings → Integrations → MQTT**
   - Host: `tcp://<ha-ip-or-broker>:1883`
   - Enable **Home Assistant Discovery**

---

### 5. Configure Tesserae (The E-Ink / Art Dashboard)

The author of the Reddit post created **Tesserae** (`dmellok/tesserae`) with the **Backyard Birds** widget:

1. Open `http://<server-ip>:8765` and complete initial setup.
2. Go to **Widgets / Catalog** and install **Backyard Birds** (or [Specimen Sheet](https://github.com/dmellok/tesserae-widget-specimen-sheet)).
3. In the widget settings:
   - **BirdNET-Go address**: `http://birdnet-go:8080` (or `http://<server-ip>:8080`)
   - **Layout**: Choose between *Field log*, *Latest visitor*, *Specimen sheet (Cluster)*, *Book plate*, *Folio plate*, *Cyanotype*, or *Postage stamp*.
   - **Plates**: Uses classic public domain plates (Audubon, Gould, Lear) from Wikimedia Commons.
   - **AI Paintings (Optional)**: If you provide a [fal.ai](https://fal.ai) API key, it will paint birds missing from historical folios in 47 art styles.
4. **Display Output**:
   - Web view: View live on any tablet or browser.
   - E-Ink display: Tesserae directly streams dithered images to Seeed reTerminal, XIAO EE02, Pimoroni Inky Impression, jailbroken Kindles (KOReader), TRMNL, and M5Paper displays over REST or MQTT.

---

### 6. Connect to Home Assistant

1. **Template Sensors**:
   Copy `home-assistant/templates/birds.yaml` to your Home Assistant `<config>/templates/birds.yaml`.
   Ensure your `configuration.yaml` contains:
   ```yaml
   template: !include_dir_merge_list templates/
   ```
2. **New Species Notifications**:
   Copy `home-assistant/automations/bird_new_species.yaml` to `<config>/automations/`.
3. **Lovelace Dashboard**:
   - In Home Assistant, create a new Dashboard.
   - Open the Raw Configuration Editor (three dots top right) and paste `home-assistant/dashboards/birds.yaml`.
   - Install **Mushroom** and **ApexCharts-Card** from HACS.
