# Bjorn

Monitor Bjorn security scanner status and view alive hosts on your LAN.

## Description

Connects to a Bjorn instance (https://github.com/infinition/Bjorn) running on your local network and displays:
- Number of alive hosts detected
- Orchestrator running/stopped status
- List of discovered hosts with open ports
- Connection status and errors

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

- **Up/Down**: Scroll through the host list
- **Select**: Toggle Bjorn orchestrator (start/stop)
- **Back**: Exit to menu

### Display

The app shows three sections:

1. **Title bar**: "Bjorn" title and alive host count
2. **Status line**: Orchestrator state (running/stopped) and connection status
3. **Host list**: Scrollable list of discovered IPs with their open ports

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
- Shows up to 50 hosts with 5 ports each (truncated for display)
- Request timeout: 8 seconds
- Non-blocking network operations
- Resilient app directory resolution (works in multiple mount paths)
- Uses LORES mode (160x120) for efficient display

### API Response Formats (Verified from Bjorn Source)

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
Ports are returned as strings (split from semicolon-separated CSV data).

**`/get_web_delay`** (from `infinition/Bjorn/webapp.py`):
```json
{"web_delay": 2}
```
This is the web UI refresh rate, typically 2 seconds. The badge uses `max(30, web_delay)` to avoid polling too frequently.

## Troubleshooting

**"cannot connect" error**:
- Verify Wi-Fi credentials in Settings
- Check that your badge can reach your network

**"fetch failed" error**:
- Verify BJORN_HOST in config.py matches your Bjorn instance
- Check that Bjorn is running and accessible
- Ensure your badge and Bjorn are on the same network

**"no hosts found"**:
- Bjorn may not have scanned yet
- Toggle the orchestrator with Select to start scanning
- Wait for Bjorn to complete a scan cycle

## Notes

- The icon is a placeholder. Contributions welcome!
- Display works best with low to moderate numbers of hosts (< 50)
- Very large port lists are truncated to save space
