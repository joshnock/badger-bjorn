"""
Monitor Bjorn security scanner status from your badge.

Connects to a Bjorn instance on your LAN and displays network scan results,
alive hosts, and orchestrator status. Select button toggles start/stop.

Configure Wi-Fi in Settings and update BJORN_HOST in config.py if needed.

Controls:
* Up/Down = Scroll host list
* Select = Toggle orchestrator start/stop
* Back = Exit
"""

import os
import sys
import json
import requests
import missing_details

APP_DIRS = ("/remote/apps/bjorn", "/system/apps/bjorn", "/apps/bjorn", "/bjorn")
APP_DIR = next(path for path in APP_DIRS if is_dir(path))
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

import config

MISSING = missing_details.missing("WIFI_SSID")
if not MISSING:
    import wifi

badge.mode(LORES | VSYNC)

WIDTH, HEIGHT = 160, 120

white = color.rgb(242, 245, 243)
text = color.rgb(228, 235, 230)
muted = color.rgb(144, 150, 146)
green = color.rgb(95, 237, 131)
red = color.rgb(255, 80, 80)
amber = color.rgb(255, 180, 50)
bg = color.rgb(16, 20, 17)

label_font = font.sins
value_font = font.bacteria
status_font = font.futile

TITLE_H = 14
STATUS_H = 24
HOST_LIST_TOP = TITLE_H + STATUS_H
HOST_LINE_H = 10
FETCH_EVERY = 30_000
RETRY_AFTER = 15_000
REQUEST_TIMEOUT = 8

netkb_data = None
orchestrator_running = None
poll_delay = 30
last_status = "initializing..."
last_error = None
fetched_at = None
next_fetch = 0
scroll_offset = 0
last_toggle = 0
TOGGLE_COOLDOWN = 2000

WIFI_TIMEOUT = 10
WIFI_RETRIES = 100000


def fetch_json(url, method="GET", data=None):
    """Fetch JSON from Bjorn API with timeout."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
        else:
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            raise OSError("HTTP %d" % response.status_code)
        
        result = response.json()
        response.close()
        return result
    except Exception as e:
        if hasattr(response, 'close'):
            response.close()
        raise


def fetch_netkb():
    """Get alive hosts and port information."""
    global netkb_data, last_error, last_status, fetched_at
    try:
        url = "%s/netkb_data_json" % config.BJORN_HOST
        data = fetch_json(url)
        if isinstance(data, dict):
            netkb_data = data
            last_error = None
            last_status = "connected"
            fetched_at = badge.ticks
        else:
            raise ValueError("Invalid response format")
    except Exception as e:
        last_error = "%s: %s" % (type(e).__name__, str(e)[:30])
        last_status = "fetch failed"


def fetch_web_delay():
    """Get recommended poll interval from Bjorn (web UI refresh rate)."""
    global poll_delay
    try:
        url = "%s/get_web_delay" % config.BJORN_HOST
        data = fetch_json(url)
        if isinstance(data, dict) and "web_delay" in data:
            web_delay = int(data.get("web_delay", 30))
            poll_delay = max(30, web_delay)
    except Exception:
        pass


def toggle_orchestrator():
    """Start or stop the Bjorn orchestrator."""
    global orchestrator_running, last_error, last_status, last_toggle
    
    if badge.ticks - last_toggle < TOGGLE_COOLDOWN:
        return
    
    last_toggle = badge.ticks
    
    try:
        if orchestrator_running:
            url = "%s/stop_orchestrator" % config.BJORN_HOST
            action = "stopping"
        else:
            url = "%s/start_orchestrator" % config.BJORN_HOST
            action = "starting"
        
        last_status = action + "..."
        fetch_json(url, method="POST")
        orchestrator_running = not orchestrator_running
        last_status = "connected"
        last_error = None
    except Exception as e:
        last_error = "%s: %s" % (type(e).__name__, str(e)[:30])
        last_status = "toggle failed"


def extract_host_list():
    """Extract host information from netkb_data.
    
    Expected format: {"ips": [...], "ports": {ip: [port_strings]}, "actions": [...]}
    """
    if not netkb_data or not isinstance(netkb_data, dict):
        return []
    
    ips = netkb_data.get("ips", [])
    ports_dict = netkb_data.get("ports", {})
    
    if not isinstance(ips, list) or not isinstance(ports_dict, dict):
        return []
    
    hosts = []
    for ip in ips[:50]:
        if not ip or not isinstance(ip, str):
            continue
        
        ports = ports_dict.get(ip, [])
        if isinstance(ports, list) and ports:
            port_str = ",".join(str(p) for p in ports[:5])
            if len(ports) > 5:
                port_str += "..."
        else:
            port_str = "no ports"
        
        hosts.append((ip, port_str))
    
    return hosts


def draw_title():
    """Draw app title bar."""
    screen.pen = green
    screen.font = status_font
    screen.text("Bjorn", 4, 2)
    
    host_count = len(extract_host_list())
    count_text = "%d alive" % host_count
    count_w = screen.measure_text(count_text)[0]
    screen.pen = muted
    screen.text(count_text, WIDTH - count_w - 4, 2)


def draw_status():
    """Draw orchestrator status and connection state."""
    y = TITLE_H + 2
    
    screen.font = label_font
    screen.pen = muted
    screen.text("status:", 4, y)
    
    if orchestrator_running is not None:
        status_text = "running" if orchestrator_running else "stopped"
        status_color = green if orchestrator_running else amber
    else:
        status_text = last_status
        status_color = muted
    
    screen.pen = status_color
    screen.text(status_text, 36, y)
    
    if last_error:
        err_short = last_error[:18]
        err_w = screen.measure_text(err_short)[0]
        screen.pen = red
        screen.text(err_short, WIDTH - err_w - 4, y)


def draw_host_list():
    """Draw scrollable list of alive hosts with ports."""
    hosts = extract_host_list()
    
    if not hosts:
        screen.font = label_font
        screen.pen = muted
        msg = "no hosts found" if netkb_data else "fetching..."
        msg_w = screen.measure_text(msg)[0]
        screen.text(msg, (WIDTH - msg_w) // 2, HOST_LIST_TOP + 20)
        return
    
    screen.pen = color.rgb(30, 34, 30)
    screen.line(0, HOST_LIST_TOP, WIDTH, HOST_LIST_TOP)
    
    y = HOST_LIST_TOP + 2
    max_visible = (HEIGHT - HOST_LIST_TOP - 2) // HOST_LINE_H
    
    start_idx = scroll_offset
    end_idx = min(start_idx + max_visible, len(hosts))
    
    screen.font = label_font
    for i in range(start_idx, end_idx):
        ip, ports = hosts[i]
        
        screen.pen = white
        screen.text(ip[:15], 4, y)
        
        screen.pen = muted
        port_text = ports[:20]
        screen.text(port_text, 4, y + HOST_LINE_H // 2)
        
        y += HOST_LINE_H
        
        if y + HOST_LINE_H > HEIGHT:
            break
    
    if len(hosts) > max_visible:
        screen.pen = muted
        indicator = "^" if scroll_offset > 0 else " "
        indicator += "v" if end_idx < len(hosts) else " "
        screen.text(indicator, WIDTH - 8, HOST_LIST_TOP + 2)


def fetch_due():
    """Fetch data when scheduled."""
    global next_fetch
    
    if not wifi.is_connected():
        return
    
    if badge.ticks >= next_fetch:
        fetch_netkb()
        
        if fetched_at == badge.ticks:
            fetch_web_delay()
        
        interval = FETCH_EVERY if last_error is None else RETRY_AFTER
        next_fetch = badge.ticks + min(interval, poll_delay * 1000)


def wait_page(heading, message):
    """Show waiting screen."""
    screen.pen = bg
    screen.rectangle(0, 0, WIDTH, HEIGHT)
    
    screen.font = status_font
    screen.pen = green
    w, _ = screen.measure_text(heading)
    screen.text(heading, (WIDTH - w) // 2, 40)
    
    screen.font = label_font
    screen.pen = muted
    screen.text(message, 10, 60, align=image.CENTER)


def connecting():
    """Connect to WiFi with status display."""
    while MISSING:
        missing_details.show(MISSING, lambda: None)
        badge.update()
    
    reason = None
    while True:
        code, saying = wifi.status()
        if code < 0:
            reason = saying
        
        if wifi.connect():
            return
        
        if reason:
            wait_page("cannot connect", reason + "\n\nRetrying...")
        else:
            wait_page("connecting...", saying)
        
        badge.update()


wait_page("starting up...", "Connecting to WiFi")
badge.update()

if not MISSING:
    wifi.connect(timeout=WIFI_TIMEOUT, retries=WIFI_RETRIES)

connecting()

max_scroll = 0

while True:
    if badge.pressed(BUTTON_BACK):
        break
    
    hosts = extract_host_list()
    max_visible = (HEIGHT - HOST_LIST_TOP - 2) // HOST_LINE_H
    max_scroll = max(0, len(hosts) - max_visible)
    
    if badge.pressed(BUTTON_UP):
        scroll_offset = max(0, scroll_offset - 1)
    
    if badge.pressed(BUTTON_DOWN):
        scroll_offset = min(max_scroll, scroll_offset + 1)
    
    if badge.pressed(BUTTON_SELECT):
        toggle_orchestrator()
    
    fetch_due()
    
    screen.pen = bg
    screen.rectangle(0, 0, WIDTH, HEIGHT)
    
    draw_title()
    draw_status()
    draw_host_list()
    
    badge.update()
