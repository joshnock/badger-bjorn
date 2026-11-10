"""
Bjorn security scanner status monitor with colorized e-paper layout.

Displays network scan progress with Viking-themed sprites, stats, and status.
Select button toggles orchestrator start/stop.

Configure Wi-Fi in Settings and BJORN_HOST in config.py if needed.

Controls:
* Select = Toggle orchestrator start/stop
* Back = Exit
"""

import os
import sys
import json
import requests
import missing_details
import random

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

# Palette constants from the art pack
PAPER    = color.rgb(244, 234, 208)
SHADE    = color.rgb(221, 205, 166)
INK      = color.rgb(35, 29, 41)
INK_SOFT = color.rgb(107, 90, 117)
STEEL    = color.rgb(141, 145, 174)
BONE     = color.rgb(255, 250, 238)
BEARD    = color.rgb(168, 133, 132)
SKIN     = color.rgb(224, 169, 159)
GREEN    = color.rgb(63, 143, 79)
AMBER    = color.rgb(217, 152, 42)
RED      = color.rgb(185, 71, 59)
TEAL     = color.rgb(47, 152, 163)

# Font offsets (from STYLE_GUIDE.md - may need device verification)
SMART_OFFSET = 4  # cap top is 4 rows below text y for font.smart
SINS_OFFSET = 3   # cap top is 3 rows below text y for font.sins

# Load all assets at module scope
title_png = image.load("assets/ui/title_bjorn_53x10.png")
frise_png = image.load("assets/ui/frise_153x9.png")

icon_wifi = image.load("assets/icons/icon_wifi_14.png")
icon_wifi_off = image.load("assets/icons/icon_wifi_off_14.png")
icon_connected = image.load("assets/icons/icon_connected_14.png")
icon_disconnected = image.load("assets/icons/icon_disconnected_14.png")
icon_target = image.load("assets/icons/icon_target_14.png")
icon_port = image.load("assets/icons/icon_port_14.png")
icon_vuln = image.load("assets/icons/icon_vuln_14.png")
icon_cred = image.load("assets/icons/icon_cred_14.png")

# Bjorn sprite strip: idle, happy, cheeky, scan, scan2, offline
bjorn_sheet = image.load("assets/sprites/bjorn_strip_52.png").spritesheet(6, 1)
SPRITE_IDLE = 0
SPRITE_HAPPY = 1
SPRITE_CHEEKY = 2
SPRITE_SCAN = 3
SPRITE_SCAN2 = 4
SPRITE_OFFLINE = 5

# State
netkb_data = None
orchestrator_running = None
bjorn_reachable = True
last_error = None
next_fetch = 0
last_toggle = 0
TOGGLE_COOLDOWN = 2000
poll_delay = 30
FETCH_EVERY = 30_000
RETRY_AFTER = 15_000
REQUEST_TIMEOUT = 8

# Animation state
current_sprite = SPRITE_IDLE
next_sprite_swap = 0
scan_frame_toggle = False

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
    global netkb_data, last_error, bjorn_reachable
    try:
        url = "%s/netkb_data_json" % config.BJORN_HOST
        data = fetch_json(url)
        if isinstance(data, dict):
            netkb_data = data
            last_error = None
            bjorn_reachable = True
        else:
            raise ValueError("Invalid response format")
    except Exception as e:
        last_error = "%s: %s" % (type(e).__name__, str(e)[:30])
        bjorn_reachable = False


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
    global orchestrator_running, last_error, last_toggle
    
    if badge.ticks - last_toggle < TOGGLE_COOLDOWN:
        return
    
    last_toggle = badge.ticks
    
    try:
        if orchestrator_running:
            url = "%s/stop_orchestrator" % config.BJORN_HOST
        else:
            url = "%s/start_orchestrator" % config.BJORN_HOST
        
        fetch_json(url, method="POST")
        orchestrator_running = not orchestrator_running
        last_error = None
    except Exception as e:
        last_error = "%s: %s" % (type(e).__name__, str(e)[:30])


def count_targets():
    """Count alive targets from netkb_data."""
    if not netkb_data or not isinstance(netkb_data, dict):
        return 0
    ips = netkb_data.get("ips", [])
    return len(ips) if isinstance(ips, list) else 0


def count_ports():
    """Count unique ports from netkb_data."""
    if not netkb_data or not isinstance(netkb_data, dict):
        return 0
    ports_dict = netkb_data.get("ports", {})
    if not isinstance(ports_dict, dict):
        return 0
    unique_ports = set()
    for ip, port_list in ports_dict.items():
        if isinstance(port_list, list):
            unique_ports.update(port_list)
    return len(unique_ports)


def get_action_name():
    """Get current action name from netkb_data (or placeholder)."""
    if not netkb_data or not isinstance(netkb_data, dict):
        return None
    actions = netkb_data.get("actions", [])
    if isinstance(actions, list) and len(actions) > 0:
        return actions[-1]
    return None


def get_subnet():
    """Get subnet being scanned (placeholder - extract from netkb_data if available)."""
    # This would come from Bjorn data if available
    # For now, show a placeholder
    return "192.168.50.0/24"


def update_sprite():
    """Update Bjorn sprite based on state and animation timer."""
    global current_sprite, next_sprite_swap, scan_frame_toggle
    
    now = badge.ticks
    if now < next_sprite_swap:
        return
    
    # Schedule next swap in 2-4 seconds (random)
    next_sprite_swap = now + random.randint(2000, 4000)
    
    wifi_up = wifi.is_connected()
    
    # Offline state: no wifi or Bjorn unreachable
    if not wifi_up or not bjorn_reachable:
        current_sprite = SPRITE_OFFLINE
        return
    
    # Scanning: alternate between scan frames
    if orchestrator_running:
        if scan_frame_toggle:
            current_sprite = SPRITE_SCAN2
        else:
            current_sprite = SPRITE_SCAN
        scan_frame_toggle = not scan_frame_toggle
        return
    
    # Idle: mostly idle/happy, occasional cheeky
    if random.randint(0, 9) == 0:
        current_sprite = SPRITE_CHEEKY
    elif random.randint(0, 1) == 0:
        current_sprite = SPRITE_IDLE
    else:
        current_sprite = SPRITE_HAPPY


def draw_frame():
    """Draw the 1px ink frame and fill with paper."""
    screen.pen = PAPER
    screen.rectangle(0, 0, WIDTH, HEIGHT)
    
    screen.pen = INK
    screen.line(0, 0, WIDTH - 1, 0)
    screen.line(WIDTH - 1, 0, WIDTH - 1, HEIGHT - 1)
    screen.line(WIDTH - 1, HEIGHT - 1, 0, HEIGHT - 1)
    screen.line(0, HEIGHT - 1, 0, 0)


def draw_top_bar():
    """Draw top bar with wifi icon, title, and connection icon."""
    wifi_up = wifi.is_connected()
    
    # Wifi icon at (3, 1)
    if wifi_up:
        screen.blit(icon_wifi, vec2(3, 1))
    else:
        screen.blit(icon_wifi_off, vec2(3, 1))
    
    # Title at (53, 3) - centered
    screen.blit(title_png, vec2(53, 3))
    
    # Connection icon at (143, 1)
    if bjorn_reachable and wifi_up:
        screen.blit(icon_connected, vec2(143, 1))
    else:
        screen.blit(icon_disconnected, vec2(143, 1))


def draw_rules():
    """Draw horizontal rules at y=16 and y=35."""
    screen.pen = INK
    screen.line(1, 16, WIDTH - 2, 16)
    screen.line(1, 35, WIDTH - 2, 35)


def format_stat(value):
    """Format stat number: show '--' if None, '1k+' if >=1000."""
    if value is None:
        return "--"
    if value >= 1000:
        return "1k+"
    return str(value)


def draw_stats_strip():
    """Draw stats strip with 4 cells: targets, ports, vulns, creds."""
    # Cell positions
    cells = [(1, 19), (41, 19), (81, 19), (121, 19)]
    icons = [icon_target, icon_port, icon_vuln, icon_cred]
    
    # Get values
    targets = count_targets() if bjorn_reachable else None
    ports = count_ports() if bjorn_reachable else None
    vulns = None  # Placeholder - endpoint not available yet
    creds = None  # Placeholder - endpoint not available yet
    
    values = [targets, ports, vulns, creds]
    
    # Draw separators (shade lines at x=40, 80, 120, rows 20-31)
    screen.pen = SHADE
    for x in [40, 80, 120]:
        screen.line(x, 20, x, 31)
    
    # Draw each cell
    for i, (cell_x, icon_y) in enumerate(cells):
        # Icon at (cell_x + 3, icon_y)
        screen.blit(icons[i], vec2(cell_x + 3, icon_y))
        
        # Number in font.smart at (cell_x + 19, ink_top 22)
        # ink_top 22 means text y = 22 - SMART_OFFSET = 18
        stat_text = format_stat(values[i])
        screen.font = font.smart
        screen.pen = INK
        screen.text(stat_text, cell_x + 19, 22 - SMART_OFFSET)


def draw_sprite():
    """Draw Bjorn sprite at (4, 36)."""
    screen.blit(bjorn_sheet.sprite(current_sprite, 0), vec2(4, 36))


def get_status_title():
    """Get status title text and color."""
    wifi_up = wifi.is_connected()
    
    if not wifi_up or not bjorn_reachable:
        return "OFFLINE", RED
    
    if orchestrator_running:
        return "SCANNING", AMBER
    
    return "IDLE", GREEN


def draw_status_panel():
    """Draw status panel with title, action, subnet, chip, and hint."""
    status_title, status_color = get_status_title()
    
    # Status title at x=61, ink_top 39 (text y = 39 - SMART_OFFSET)
    screen.font = font.smart
    screen.pen = status_color
    screen.text(status_title, 61, 39 - SMART_OFFSET)
    
    # Action/line 2 at x=61, ink_top 51 (text y = 51 - SINS_OFFSET)
    screen.font = font.sins
    screen.pen = INK
    
    action = get_action_name()
    if action:
        # Truncate to fit ~17 chars
        action_text = action[:17]
    else:
        action_text = "orchestrator idle"
    
    screen.text(action_text, 61, 51 - SINS_OFFSET)
    
    # Subnet/line 3 at x=61, ink_top 61 (text y = 61 - SINS_OFFSET)
    screen.pen = INK_SOFT
    subnet_text = get_subnet()[:17]  # Truncate to fit
    screen.text(subnet_text, 61, 61 - SINS_OFFSET)
    
    # Chip at (61, 73, 25, 11)
    if orchestrator_running:
        chip_fill = GREEN
        chip_text = "RUN"
    else:
        chip_fill = RED
        chip_text = "STOP"
    
    # Fill chip
    screen.pen = chip_fill
    screen.rectangle(61, 73, 25, 11)
    
    # Chip outline
    screen.pen = INK
    screen.line(61, 73, 85, 73)
    screen.line(85, 73, 85, 83)
    screen.line(85, 83, 61, 83)
    screen.line(61, 83, 61, 73)
    
    # Chip text in BONE, centered
    screen.font = font.sins
    screen.pen = BONE
    chip_w, _ = screen.measure_text(chip_text)
    chip_x = 61 + (25 - chip_w) // 2
    screen.text(chip_text, chip_x, 75 - SINS_OFFSET)
    
    # Hint at x=90, ink_top 75 (text y = 75 - SINS_OFFSET)
    screen.pen = INK_SOFT
    screen.text("sel: stop" if orchestrator_running else "sel: start", 90, 75 - SINS_OFFSET)


def draw_frise():
    """Draw frise divider at (3, 89)."""
    screen.blit(frise_png, vec2(3, 89))


def word_wrap(text, max_width):
    """Simple word wrap to fit text in max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    
    screen.font = font.sins
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        w, _ = screen.measure_text(test_line)
        
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines


def draw_comment():
    """Draw Bjorn's comment (2 lines max) at x=4, ink_tops 100 and 109."""
    # Get comment text based on state
    wifi_up = wifi.is_connected()
    
    if not wifi_up:
        comment = "Bjorn is napping. Check WIFI_SSID in config"
    elif not bjorn_reachable:
        comment = "Bjorn is unreachable. Check BJORN_HOST in config or start Bjorn"
    elif last_error:
        comment = "Error: %s" % last_error[:40]
    elif orchestrator_running:
        comment = "Charting the fjords of your network, host by host..."
    elif netkb_data:
        targets = count_targets()
        if targets == 0:
            comment = "No quarry yet. Bid me hunt with select"
        else:
            comment = "All quiet in the longhouse. Resting until the next scan"
    else:
        comment = "Awaiting orders from the chieftain..."
    
    # Word wrap to 152px (about 28 chars for font.sins)
    lines = word_wrap(comment, 152)[:2]  # Max 2 lines
    
    screen.font = font.sins
    screen.pen = INK
    
    # Line 1 at ink_top 100 (text y = 100 - SINS_OFFSET)
    if len(lines) > 0:
        screen.text(lines[0], 4, 100 - SINS_OFFSET)
    
    # Line 2 at ink_top 109 (text y = 109 - SINS_OFFSET)
    if len(lines) > 1:
        screen.text(lines[1], 4, 109 - SINS_OFFSET)


def fetch_due():
    """Fetch data when scheduled."""
    global next_fetch
    
    if not wifi.is_connected():
        return
    
    if badge.ticks >= next_fetch:
        fetch_netkb()
        
        if bjorn_reachable:
            fetch_web_delay()
        
        interval = FETCH_EVERY if bjorn_reachable else RETRY_AFTER
        next_fetch = badge.ticks + min(interval, poll_delay * 1000)


def wait_page(heading, message):
    """Show waiting screen."""
    screen.pen = PAPER
    screen.rectangle(0, 0, WIDTH, HEIGHT)
    
    screen.font = font.smart
    screen.pen = GREEN
    w, _ = screen.measure_text(heading)
    screen.text(heading, (WIDTH - w) // 2, 40)
    
    screen.font = font.sins
    screen.pen = INK_SOFT
    lines = word_wrap(message, WIDTH - 20)
    y = 60
    for line in lines[:3]:
        w, _ = screen.measure_text(line)
        screen.text(line, (WIDTH - w) // 2, y)
        y += 9


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
            wait_page("cannot connect", reason + " Retrying...")
        else:
            wait_page("connecting...", saying)
        
        badge.update()


# Startup
wait_page("starting up...", "Connecting to WiFi")
badge.update()

if not MISSING:
    wifi.connect(timeout=WIFI_TIMEOUT, retries=WIFI_RETRIES)

connecting()

# Main loop
while True:
    if badge.pressed(BUTTON_BACK):
        break
    
    if badge.pressed(BUTTON_SELECT):
        toggle_orchestrator()
    
    update_sprite()
    fetch_due()
    
    # Draw everything
    draw_frame()
    draw_top_bar()
    draw_rules()
    draw_stats_strip()
    draw_sprite()
    draw_status_panel()
    draw_frise()
    draw_comment()
    
    badge.update()
