#!/usr/bin/env python3
"""
InkJoy Muse Bridge for Backyard Birds
Sends bird plates, specimen sheets, or dashboard renders directly to your InkJoy Muse frame
using the InkJoy OpenAPI.
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SERVERS = {
    "global": "https://openapi.inkjoyframe.com",
    "china": "https://openapi.advisor.epaperframe.com",
}


def load_env():
    """Load variables from .env file in current or parent directories if it exists."""
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path("/config/.env"),
        Path("/homeassistant/.env"),
        Path(".env"),
    ]
    for env_file in candidates:
        if env_file.is_file():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
            break


class InkJoyClient:
    def __init__(self, server_url="https://openapi.inkjoyframe.com", token=None):
        self.server_url = server_url.rstrip("/")
        self.token = token

    def login(self, email, password):
        url = f"{self.server_url}/api/v1/auth/login"
        payload = json.dumps({"email": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "BirdNET-InkJoyBridge/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0:
                    self.token = data["data"]["token"]
                    return data["data"]
                raise RuntimeError(data.get("msg", "Login failed"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise RuntimeError(f"HTTP Error {e.code}: {err_body}")

    def get_devices(self):
        if not self.token:
            raise RuntimeError("Must login before fetching devices")
        url = f"{self.server_url}/api/v1/devices"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "BirdNET-InkJoyBridge/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                return data.get("data", [])
            raise RuntimeError(data.get("msg", "Failed to get devices"))

    def publish_image(self, device_id, image_bytes, filename="bird.png"):
        if not self.token:
            raise RuntimeError("Must login before publishing image")
        url = f"{self.server_url}/api/v1/devices/{device_id}/publish"

        boundary = "----WebKitFormBoundary" + os.urandom(16).hex()
        content_type = mimetypes.guess_type(filename)[0] or "image/png"

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "BirdNET-InkJoyBridge/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                return data.get("data")
            raise RuntimeError(data.get("msg", "Failed to publish image"))


def main():
    load_env()

    parser = argparse.ArgumentParser(description="InkJoy Muse BirdNET Bridge")
    parser.add_argument("--email", default=os.getenv("INKJOY_EMAIL"), help="InkJoy account email")
    parser.add_argument("--password", default=os.getenv("INKJOY_PASSWORD"), help="InkJoy account password")
    parser.add_argument("--device-id", default=os.getenv("INKJOY_DEVICE_ID"), help="Target InkJoy device ID")
    parser.add_argument("--list-devices", action="store_true", help="List registered InkJoy devices and exit")
    parser.add_argument("--image", help="Path or URL to an image to push to your frame")
    parser.add_argument("--tesserae-url", default=os.getenv("TESSERAE_URL", "http://homeassistant.local:8765"), help="Tesserae base URL")
    parser.add_argument("--tesserae-token", default=os.getenv("TESSERAE_TOKEN"), help="Tesserae MCP / API Bearer token (optional if loopback)")
    parser.add_argument("--page-id", default=os.getenv("TESSERAE_PAGE_ID"), help="ID of the Tesserae dashboard/page to render")
    parser.add_argument("--tesserae-render", action="store_true", help="Fetch live render from Tesserae Backyard Birds widget/dashboard and push")

    args = parser.parse_args()

    if not args.email or not args.password:
        print("❌ Error: INKJOY_EMAIL and INKJOY_PASSWORD must be provided via arguments or .env file.")
        print("Usage:")
        print("  python3 scripts/inkjoy_bridge.py --email user@example.com --password mypass --list-devices")
        sys.exit(1)

    client = InkJoyClient()
    print(f"🔐 Logging into InkJoy Cloud as {args.email}...")
    client.login(args.email, args.password)
    print("✅ Successfully authenticated!")

    devices = client.get_devices()
    if not devices:
        print("⚠️ No devices found associated with this InkJoy account.")
        sys.exit(0)

    print(f"\n📱 Discovered {len(devices)} InkJoy Frame(s):")
    for d in devices:
        dev_id = d.get("deviceId") or d.get("device_id") or d.get("id")
        dev_name = d.get("deviceName") or d.get("device_name") or d.get("name") or "Unnamed"
        model = d.get("model") or d.get("deviceModel") or "Muse"
        status = d.get("status") or d.get("onlineStatus") or "unknown"
        res = d.get("resolution") or {}
        res_str = f" ({res.get('width')}x{res.get('height')})" if res else ""
        print(f"  • Name: {dev_name} | ID: {dev_id} | Model: {model}{res_str} | Status: {status}")

    # Fallback / resolve target device ID
    first_device = devices[0]
    auto_id = first_device.get("deviceId") or first_device.get("device_id") or first_device.get("id")

    if args.list_devices or (not args.image and not args.tesserae_render):
        if not args.image and not args.tesserae_render:
            print("\n💡 Usage examples:")
            print(f"  • Push Tesserae live widget:  python3 scripts/inkjoy_bridge.py --tesserae-render")
            print(f"  • Push an image:             python3 scripts/inkjoy_bridge.py --image samples/blue_jay_1200x1600.jpg")
            print("  (Tip: set INKJOY_EMAIL and INKJOY_PASSWORD in your .env file so you don't have to re-type them)")
        sys.exit(0)

    target_id = args.device_id or auto_id
    if not target_id:
        print("❌ Could not determine a valid device ID. Full device payload:")
        print(json.dumps(devices, indent=2))
        sys.exit(1)

    # Get device panel dimensions
    target_device = next((d for d in devices if (d.get("deviceId") or d.get("id")) == target_id), first_device)
    res = target_device.get("resolution") or {}
    panel_w = res.get("width", 1200)
    panel_h = res.get("height", 1600)

    print(f"\n🚀 Preparing to push to frame '{target_device.get('deviceName', 'Muse')}' ({panel_w}x{panel_h})...")

    # If --tesserae-render is requested, fetch directly from Tesserae MCP render endpoint
    if args.tesserae_render:
        urls_to_try = [
            args.tesserae_url,
            "http://homeassistant.local:8765",
            "http://965a99d7-tesserae:8765",
            "http://tesserae:8765",
            "http://homeassistant:8765",
        ]
        candidates = list(dict.fromkeys(u.rstrip("/") for u in urls_to_try if u))

        headers = {"User-Agent": "BirdNET-Bridge/1.0"}
        if args.tesserae_token:
            headers["Authorization"] = f"Bearer {args.tesserae_token}"

        # 1. Discover saved dashboard page ID if not explicitly specified
        page_id = args.page_id
        active_base = None

        for base in candidates:
            if page_id:
                active_base = base
                break
            # Try dashboards.json or mcp pages
            for endpoint in ["/pages/dashboards.json", "/api/mcp/pages"]:
                url = f"{base}{endpoint}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        pages = data.get("pages") or []
                        if pages:
                            # Pick page named backyard/birds or first available
                            for p in pages:
                                p_name = str(p.get("name", "")).lower()
                                if "bird" in p_name or "backyard" in p_name:
                                    page_id = p.get("id")
                                    break
                            if not page_id:
                                page_id = pages[0].get("id")
                            active_base = base
                            print(f"📄 Found saved Tesserae dashboard: ID='{page_id}' (Name: '{pages[0].get('name')}') on {base}")
                            break
                except Exception:
                    continue
            if page_id:
                break

        image_data = None
        last_error = None
        search_bases = [active_base] if active_base else candidates

        for base in search_bases:
            # Build list of render endpoints to try for this dashboard
            endpoints_to_try = []
            if page_id:
                endpoints_to_try.extend([
                    f"{base}/compose/{page_id}/preview.png?w={panel_w}&h={panel_h}",
                    f"{base}/api/mcp/pages/{page_id}/preview.png?fresh=1",
                    f"{base}/compose/{page_id}/panel.png?w={panel_w}&h={panel_h}",
                ])
            # Fallback to standalone widget render
            endpoints_to_try.append(f"{base}/api/mcp/widgets/backyard_birds/render.png?w={panel_w}&h={panel_h}")

            for render_url in endpoints_to_try:
                print(f"🎨 Trying to fetch render from: {render_url}")
                req = urllib.request.Request(render_url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        image_data = resp.read()
                    print(f"✅ Render successfully generated ({len(image_data)/1024:.1f} KB)!")
                    break
                except Exception as e:
                    last_error = e
                    print(f"  ↳ Could not fetch from {render_url}: {e}")
            if image_data:
                break

        if not image_data:
            print(f"\n❌ Failed to fetch render from Tesserae after trying: {candidates}")
            print("Last error:", last_error)
            print("\nTroubleshooting tips:")
            print(" 1. Check Settings -> Apps -> Tesserae -> Configuration: make sure port 8765 is typed in and saved.")
            print(" 2. In /config/.env, set TESSERAE_URL to your Green's LAN IP, e.g. TESSERAE_URL=http://192.168.1.xxx:8765")
            sys.exit(1)

        filename = "tesserae_backyard_birds.png"
        fitted_path = None
    else:
        # User passed a local file or image URL
        local_path = None
        if args.image.startswith("http://") or args.image.startswith("https://"):
            print(f"🌐 Downloading image from: {args.image}")
            req = urllib.request.Request(args.image, headers={"User-Agent": "BirdNET-Bridge/1.0"})
            with urllib.request.urlopen(req) as resp:
                image_data = resp.read()
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(image_data)
            tmp.close()
            local_path = tmp.name
            filename = os.path.basename(urllib.parse.urlparse(args.image).path) or "bird.jpg"
        else:
            local_path = args.image
            filename = os.path.basename(args.image)

        # Auto-pad/resize to exact panel dimensions using macOS sips if needed
        fitted_path = local_path
        import shutil
        import subprocess
        if shutil.which("sips"):
            import tempfile
            tmp_fitted = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_fitted.close()
            max_dim = max(panel_w, panel_h)
            subprocess.run(["sips", "-Z", str(max_dim), local_path, "--out", tmp_fitted.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sips", "-p", str(panel_h), str(panel_w), "--padColor", "FBF9F5", tmp_fitted.name, "--out", tmp_fitted.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            fitted_path = tmp_fitted.name

        with open(fitted_path, "rb") as f:
            image_data = f.read()

    print(f"📤 Uploading {filename} ({len(image_data) / 1024:.1f} KB) to InkJoy Muse...")
    result = client.publish_image(target_id, image_data, filename)
    print("🎉 Success! Image pushed to your InkJoy Muse frame.")


if __name__ == "__main__":
    main()
