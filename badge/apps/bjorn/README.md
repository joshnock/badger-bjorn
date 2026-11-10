# Bjorn

Monitor Bjorn security scanner status with a colorized Viking-themed e-paper layout.

## Description

Connects to a Bjorn instance (https://github.com/infinition/Bjorn) running on your local network and displays scan status with a pixel-art Viking interface featuring Bjorn the badger in his horned helmet, real-time stats, and atmospheric commentary.

## Requirements

- Wi-Fi configured in Settings (WIFI_SSID and WIFI_PASSWORD in secrets.py)
- Bjorn instance running on your LAN (default: http://192.168.50.91:8000)

## Configuration

To connect to a different Bjorn host, edit `config.py` in the app directory:

```python
BJORN_HOST = "http://192.168.1.100:8000"  # Your Bjorn IP and port
```

## Usage

### Controls

- **Select**: Toggle Bjorn orchestrator (start/stop scanning)
- **Back**: Exit to menu

### Display Layout

The app uses a 160×120 colorized e-paper style layout inspired by Bjorn's original Waveshare e-paper screen:

1. **Top bar**: Wi-Fi status, "BJORN" title, and connection indicator
2. **Stats strip**: Four stats with icons
   - Targets (alive hosts)
   - Ports (unique open ports)
   - Vulns (placeholder - shows "--" until endpoint available)
   - Creds (placeholder - shows "--" until endpoint available)
3. **Left panel**: Animated 52×52 Bjorn sprite that changes based on state
   - **Idle**: Eyes open, resting
   - **Happy**: Eyes closed, smiling (also used when stopped)
   - **Cheeky**: Occasional tongue-out variant
   - **Scanning**: Glasses on, alternating horn positions
   - **Offline**: Greyed out when Wi-Fi is down or Bjorn is unreachable
4. **Right panel**: Status with color-coded title
   - **SCANNING** (amber): orchestrator is running
   - **IDLE** (green): connected but not scanning
   - **OFFLINE** (red): no Wi-Fi or Bjorn unreachable
   - Current action name (e.g., "NetworkScanner")
   - Subnet being scanned
   - RUN/STOP chip showing current state
   - Hint text for Select button
5. **Frise divider**: Viking knot pattern
6. **Comment lines**: Bjorn's atmospheric status messages

### Color Palette

The app uses a 12-color parchment-paper palette with plum-black ink and spot colors:
- Parchment paper background
- Green = good/running
- Amber = busy/scanning
- Red = errors/stopped
- Teal = Wi-Fi and credentials

### Installation

1. Copy the entire `badge/apps/bjorn/` directory to `/Volumes/BADGER/apps/bjorn/` when your badge is in USB mass storage mode

2. Update the menu to include Bjorn. Edit `/Volumes/BADGER/apps/menu/app.py` and add "bjorn" to the APP_ORDER tuple:

```python
APP_ORDER = (
    "badge",
    "contacts",
    "bjorn",        # Add this line
    "mona_paint",
    # ... rest of apps
)
```

3. Safely eject the badge and restart it

## Safety

This app only uses safe read-only endpoints:
- `GET /netkb_data_json` - Network scan results (returns `{"ips": [...], "ports": {...}}`)
- `GET /get_web_delay` - Web UI refresh delay (returns `{"web_delay": <seconds>}`)
- `POST /start_orchestrator` - Start scanning
- `POST /stop_orchestrator` - Stop scanning

No offensive operations, credential viewing, or attack execution endpoints are called.

**Note**: The `web_delay` from Bjorn is the web UI refresh rate (typically ~2 seconds), not the scan cadence. The badge clamps the poll interval to a minimum of 30 seconds to avoid excessive requests.

## Technical Details

- Polls Bjorn every 30 seconds (minimum, respects `web_delay` if larger)
- Retries failed requests after 15 seconds
- Request timeout: 8 seconds
- Non-blocking network operations
- Integer-only vec2 coordinates for pixel-perfect rendering
- Uses LORES mode (160×120) with exact palette colors
- Sprite animation: frames swap every 2-4 seconds randomly
- Font: `font.smart` for numbers and titles, `font.sins` for body text

### Font Baseline Notes

The layout assumes these font metrics from the `.ppf` files:
- `font.smart`: cap top is 4 rows below text y
- `font.sins`: cap top is 3 rows below text y
- Space width: 3px

**These offsets may need device verification.** If text appears misaligned by 1px, adjust `SMART_OFFSET` and `SINS_OFFSET` in `__init__.py`.

### Asset Structure

```
badge/apps/bjorn/
├── __init__.py           # Main app code
├── config.py             # BJORN_HOST configuration
├── icon.png              # 48×48 menu icon (Bjorn's head)
├── README.md             # This file
└── assets/
    ├── sprites/
    │   ├── bjorn_idle_52.png      # Eyes open
    │   ├── bjorn_happy_52.png     # Eyes closed, smiling
    │   ├── bjorn_cheeky_52.png    # Tongue out
    │   ├── bjorn_scan_52.png      # Scanning with glasses
    │   ├── bjorn_scan2_52.png     # Scanning, second frame
    │   ├── bjorn_offline_52.png   # Greyed out
    │   └── bjorn_strip_52.png     # All 6 frames in one sheet
    ├── icons/
    │   ├── icon_wifi_14.png
    │   ├── icon_wifi_off_14.png
    │   ├── icon_connected_14.png
    │   ├── icon_disconnected_14.png
    │   ├── icon_target_14.png
    │   ├── icon_port_14.png
    │   ├── icon_vuln_14.png
    │   └── icon_cred_14.png
    └── ui/
        ├── title_bjorn_53x10.png  # "BJORN" wordmark
        └── frise_153x9.png        # Viking knot divider
```

### API Response Formats

**`/netkb_data_json`** (from `infinition/Bjorn/utils.py`):
```json
{
  "ips": ["192.168.1.100", "192.168.1.101"],
  "ports": {
    "192.168.1.100": ["22", "80", "443"],
    "192.168.1.101": ["3306"]
  },
  "actions": ["scan_action", ...]
}
```

**`/get_web_delay`** (from `infinition/Bjorn/webapp.py`):
```json
{"web_delay": 2}
```

## Troubleshooting

**"cannot connect" error**:
- Verify Wi-Fi credentials in Settings
- Check that your badge can reach your network

**"fetch failed" / Bjorn unreachable**:
- Verify BJORN_HOST in config.py matches your Bjorn instance
- Check that Bjorn is running and accessible
- Ensure your badge and Bjorn are on the same network

**Bjorn shows OFFLINE state**:
- Sprite is greyed out when Wi-Fi is down or Bjorn cannot be reached
- Check connection status icon in top right (red X = disconnected)

**Stats show "--"**:
- Vulns and creds stats show "--" as placeholders until additional Bjorn endpoints are available
- Targets and ports should populate once Bjorn completes a scan

## Art Credits

Colorized e-paper art pack derived from Bjorn's original Waveshare e-paper status screen. Sprites adapted from Bjorn's `resources/images/status/` frames. All art follows a 12-color parchment palette with exact RGB values for pixel-perfect rendering.

Layout coordinates and palette constants are documented in the art pack's `README.md`, `STYLE_GUIDE.md`, and `AUDIT.md` (0 off-palette pixels).
