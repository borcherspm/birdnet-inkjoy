#!/usr/bin/env bash
# ==============================================================================
# Test Camera RTSP Audio Stream
# Usage: ./scripts/test_rtsp_stream.sh [RTSP_URL]
# If no URL is provided, it reads CAMERA_RTSP_URL from .env
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
fi

RTSP_URL="${1:-${CAMERA_RTSP_URL:-}}"

if [ -z "$RTSP_URL" ] || [ "$RTSP_URL" = "rtsp://admin:password@192.168.1.50:554/Streaming/Channels/101" ]; then
    echo "❌ Error: Please provide a valid RTSP URL or set CAMERA_RTSP_URL in .env"
    echo "Usage: $0 rtsp://user:pass@camera-ip:554/stream"
    exit 1
fi

echo "🔍 Probing RTSP stream for audio tracks: $RTSP_URL"

# Check if ffmpeg or ffprobe is installed locally
if command -v ffprobe &>/dev/null; then
    echo "Using local ffprobe..."
    ffprobe -hide_banner -rtsp_transport tcp -i "$RTSP_URL" -show_streams -select_streams a
elif command -v docker &>/dev/null; then
    echo "Using Docker BirdNET-Go ffmpeg container..."
    docker run --rm --entrypoint ffmpeg ghcr.io/tphakala/birdnet-go:latest \
        -hide_banner -rtsp_transport tcp -timeout 5000000 \
        -i "$RTSP_URL" -vn -t 5 -f null -
else
    echo "❌ Neither 'ffprobe' nor 'docker' was found on your PATH."
    echo "Please install ffmpeg (brew install ffmpeg) or Docker."
    exit 1
fi

echo "✅ Audio stream verification completed!"
