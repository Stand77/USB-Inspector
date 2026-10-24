#!/usr/bin/env python3
"""
USB Device Inspector
====================
Inspects currently connected USB devices and monitors for hot-plug events.

Shows device names, locations/ports, vendor info, VID:PID (with human-readable names
when known or looked up online), serial numbers, etc.
Supports hot-plugging and automatic identification from the official USB ID database.
"""

import sys
import time
import os
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

try:
    from usbmonitor import USBMonitor
    from usbmonitor.attributes import (
        ID_MODEL, ID_MODEL_FROM_DATABASE, ID_VENDOR, ID_VENDOR_FROM_DATABASE,
        ID_VENDOR_ID, ID_MODEL_ID, ID_SERIAL, DEVNAME, ID_USB_INTERFACES,
        ID_USB_CLASS_FROM_DATABASE
    )
except ImportError:
    print("Error: usb-monitor is not installed.")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("Error: rich is not installed.")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)

# Optional Windows registry access for better port info
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

console = Console()

# Cache for online USB ID database
USB_IDS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usb.ids.cache")
USB_IDS_URL = "http://www.linux-usb.org/usb.ids"
_usb_ids_db: Optional[Dict[str, Tuple[str, str]]] = None

# Known USB devices: "VID:PID" -> (Vendor Name, Product Name)
# Local curated list (highest priority). Online database is used as fallback.
KNOWN_DEVICES = {
    # Logitech
    "046D:C22F": ("Logitech, Inc.", "Cordless RumblePad 2"),
    "046D:C219": ("Logitech, Inc.", "Cordless RumblePad 2"),
    "046D:C21D": ("Logitech, Inc.", "F310 Gamepad (XInput)"),
    "046D:C21E": ("Logitech, Inc.", "F510 Gamepad (XInput)"),
    "046D:C21F": ("Logitech, Inc.", "F710 Wireless Gamepad (XInput)"),
    "046D:C52B": ("Logitech, Inc.", "Unifying Receiver"),
    "046D:C532": ("Logitech, Inc.", "Unifying Receiver"),
    "046D:C52F": ("Logitech, Inc.", "Unifying Receiver"),
    "046D:C534": ("Logitech, Inc.", "Unifying Receiver"),
    "046D:C31C": ("Logitech, Inc.", "Keyboard K120"),
    "046D:C31B": ("Logitech, Inc.", "Compact Keyboard K300"),
    "046D:C318": ("Logitech, Inc.", "Illuminated Keyboard"),
    "046D:C317": ("Logitech, Inc.", "Wave Corded Keyboard"),
    "046D:C082": ("Logitech, Inc.", "G Pro Wireless Mouse"),
    "046D:C08B": ("Logitech, Inc.", "G502 SE HERO Gaming Mouse"),
    "046D:C07D": ("Logitech, Inc.", "G502 Mouse"),
    "046D:C084": ("Logitech, Inc.", "G203 Gaming Mouse"),
    "046D:C09D": ("Logitech, Inc.", "G102 LIGHTSYNC Gaming Mouse"),
    "046D:C092": ("Logitech, Inc.", "G102/G203 LIGHTSYNC Gaming Mouse"),
    "046D:C24A": ("Logitech, Inc.", "G600 Gaming Mouse"),
    "046D:C24C": ("Logitech, Inc.", "G400s Optical Mouse"),
    "046D:C245": ("Logitech, Inc.", "G400 Optical Mouse"),
    "046D:C246": ("Logitech, Inc.", "Gaming Mouse G300"),
    "046D:C247": ("Logitech, Inc.", "G100S Optical Gaming Mouse"),
    "046D:C22D": ("Logitech, Inc.", "G510 Gaming Keyboard"),
    "046D:C228": ("Logitech, Inc.", "G19 Gaming Keyboard"),
    "046D:C226": ("Logitech, Inc.", "G15 Refresh Keyboard"),
    "046D:C248": ("Logitech, Inc.", "G105 Gaming Keyboard"),
    "046D:C336": ("Logitech, Inc.", "G213 Prodigy Gaming Keyboard"),
    "046D:C339": ("Logitech, Inc.", "PRO Gaming Keyboard"),
    "046D:082D": ("Logitech, Inc.", "HD Pro Webcam C920"),
    "046D:0825": ("Logitech, Inc.", "Webcam C270"),
    "046D:081B": ("Logitech, Inc.", "Webcam C310"),
    "046D:0809": ("Logitech, Inc.", "Webcam Pro 9000"),
    # Realtek / RTL-SDR
    "0BDA:2832": ("Realtek Semiconductor Corp.", "RTL2832U DVB-T / RTL-SDR"),
    "0BDA:2838": ("Realtek Semiconductor Corp.", "RTL2838 DVB-T / RTL-SDR (rtl-sdr.com)"),
    "0BDA:2830": ("Realtek Semiconductor Corp.", "RTL2830 DVB-T / RTL-SDR"),
    "0BDA:8152": ("Realtek Semiconductor Corp.", "RTL8152 USB Ethernet"),
    "0BDA:8153": ("Realtek Semiconductor Corp.", "RTL8153 USB Ethernet"),
    # Microsoft
    "045E:028E": ("Microsoft Corp.", "Xbox 360 Controller"),
    "045E:02EA": ("Microsoft Corp.", "Xbox One Controller"),
    "045E:02D1": ("Microsoft Corp.", "Xbox One Controller"),
    "045E:0745": ("Microsoft Corp.", "Nano Transceiver v1.0 for Bluetooth"),
    # MediaTek / Alexa
    "0E8D:2000": ("MediaTek Inc.", "PreLoader USB VCOM (Android / Alexa / MediaTek device)"),
    "0E8D:2001": ("MediaTek Inc.", "PreLoader USB VCOM"),
    "0E8D:0002": ("MediaTek Inc.", "MT65xx Preloader"),
    "0E8D:2008": ("MediaTek Inc.", "MediaTek USB VCOM"),
    # Spectrum Interlink / RealFlight
    "1781:0E5A": ("Spectrum Interlink", "InterLink DX Flight Simulator Controller (RealFlight)"),
    "1781:0E5B": ("Spectrum Interlink", "Flight Simulator Controller"),
    "1781:0E50": ("Spectrum Interlink", "InterLink Controller"),
    # Other common
    "1B1C:1B3D": ("Corsair", "K70 RGB Keyboard"),
    "1532:0067": ("Razer USA, Ltd.", "DeathAdder"),
    "1532:0084": ("Razer USA, Ltd.", "DeathAdder Chroma"),
}


def load_usb_ids_database(force_refresh: bool = False) -> Dict[str, Tuple[str, str]]:
    """Download (or load cached) the official usb.ids database and parse it."""
    global _usb_ids_db
    if _usb_ids_db is not None and not force_refresh:
        return _usb_ids_db

    content = None
    if os.path.exists(USB_IDS_CACHE) and not force_refresh:
        try:
            with open(USB_IDS_CACHE, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            content = None

    if content is None:
        try:
            console.print("[dim]Downloading USB ID database (one-time)...[/dim]")
            with urllib.request.urlopen(USB_IDS_URL, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            try:
                with open(USB_IDS_CACHE, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass
        except Exception:
            content = ""

    db: Dict[str, Tuple[str, str]] = {}
    if content:
        current_vid = None
        current_vendor = None
        for line in content.splitlines():
            if not line or line.startswith("#"):
                continue
            if line.startswith("\t") and not line.startswith("\t\t"):
                if current_vid:
                    parts = line.strip().split(None, 1)
                    if len(parts) >= 2:
                        pid = parts[0].upper()
                        product = parts[1].strip()
                        key = f"{current_vid}:{pid}"
                        db[key] = (current_vendor or "Unknown Vendor", product)
            else:
                parts = line.split(None, 1)
                if len(parts) >= 2 and len(parts[0]) == 4:
                    current_vid = parts[0].upper()
                    current_vendor = parts[1].strip()

    _usb_ids_db = db
    return db


def lookup_online(vid: str, pid: str) -> Optional[Tuple[str, str]]:
    """Look up VID:PID in the official USB ID database."""
    db = load_usb_ids_database()
    key = f"{vid.upper()}:{pid.upper()}"
    return db.get(key)


def get_known_device(device_info: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Return (vendor_name, product_name) if known (local or online), else None."""
    vid = (device_info.get(ID_VENDOR_ID) or "").upper()
    pid = (device_info.get(ID_MODEL_ID) or "").upper()
    key = f"{vid}:{pid}"

    if key in KNOWN_DEVICES:
        return KNOWN_DEVICES[key]

    online = lookup_online(vid, pid)
    if online:
        return online

    return None


def get_readable_ids(device_info: Dict[str, Any]) -> str:
    """Return human-readable VID and PID text."""
    known = get_known_device(device_info)
    vid = (device_info.get(ID_VENDOR_ID) or "????").upper()
    pid = (device_info.get(ID_MODEL_ID) or "????").upper()

    if known:
        vendor_name, product_name = known
        return (
            f"Vendor ID ({vid}): {vendor_name}\n"
            f"  Device ID ({pid}): {product_name}"
        )
    return f"VID:PID:  {vid}:{pid}"


def get_device_name(device_info: Dict[str, Any]) -> str:
    """Extract the most human-readable device name available."""
    known = get_known_device(device_info)
    if known:
        return known[1]

    for key in (ID_MODEL_FROM_DATABASE, ID_MODEL, ID_VENDOR_FROM_DATABASE, ID_VENDOR):
        name = device_info.get(key)
        if name and name.strip() and name not in ("None", "n/a", ""):
            return name.replace("_", " ").strip()
    return "Unknown Device"


def get_vendor_name(device_info: Dict[str, Any]) -> str:
    """Extract vendor name."""
    known = get_known_device(device_info)
    if known:
        return known[0]

    for key in (ID_VENDOR_FROM_DATABASE, ID_VENDOR):
        name = device_info.get(key)
        if name and name.strip() and name not in ("None", "n/a", ""):
            return name.replace("_", " ").strip()
    return "Unknown Vendor"


def get_vid_pid(device_info: Dict[str, Any]) -> str:
    """Format VID:PID."""
    vid = device_info.get(ID_VENDOR_ID, "????")
    pid = device_info.get(ID_MODEL_ID, "????")
    return f"{vid}:{pid}"


def get_windows_location_info(device_id: str) -> Optional[str]:
    """On Windows, look up the LocationInformation string (e.g. Port_#0002.Hub_#0004)."""
    if not HAS_WINREG or not sys.platform.startswith("win"):
        return None

    try:
        reg_path = device_id.replace("/", "\\")
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            rf"SYSTEM\CurrentControlSet\Enum\{reg_path}",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        )
        try:
            value, _ = winreg.QueryValueEx(key, "LocationInformation")
            if value and isinstance(value, str) and value.strip():
                return value.strip()
        finally:
            winreg.CloseKey(key)
    except OSError:
        pass
    return None


def get_location(device_id: str, device_info: Dict[str, Any]) -> str:
    """Get the best available location / port identifier."""
    loc_info = get_windows_location_info(device_id)
    if loc_info:
        return f"{loc_info}  ({device_id})"

    devname = device_info.get(DEVNAME)
    if devname and devname.strip():
        return devname
    return device_id


def get_likely_purpose(device_info: Dict[str, Any]) -> str:
    """Generate a human-friendly summary of what the device is likely used for."""
    vid = (device_info.get(ID_VENDOR_ID) or "").upper()
    pid = (device_info.get(ID_MODEL_ID) or "").upper()

    # Hard-coded high-priority matches (always win)
    if vid == "1781" and pid == "0E5A":
        return "Spectrum Interlink DX Flight Simulator Controller (RealFlight)"
    if vid == "1781":
        return "Spectrum Interlink flight simulator controller"

    known = get_known_device(device_info)
    if known:
        vendor_name, product_name = known
        return f"{product_name} ({vendor_name})"
    usb_class = (device_info.get(ID_USB_CLASS_FROM_DATABASE) or "").lower()
    interfaces = device_info.get(ID_USB_INTERFACES) or ()
    interfaces_str = " ".join(str(i) for i in interfaces).upper()

    rtl_sdr_pids = {"2832", "2838", "2830", "2831", "2834", "2836", "2837", "2839", "2840"}
    if vid == "0BDA" and pid in rtl_sdr_pids:
        return "RTL-SDR receiver (rtl-sdr.com / Realtek RTL2832U)"

    if vid == "1781":
        return "Spectrum Interlink DX Flight Simulator Controller (RealFlight)"

    if vid == "0E8D" and pid in {"2000", "2001", "0002", "0003", "2008"}:
        return "MediaTek PreLoader / VCOM (Android or Alexa/Echo device in boot/recovery mode)"

    vendor_hint = ""
    if vid == "046D":
        vendor_hint = "Logitech "
    elif vid == "045E":
        vendor_hint = "Microsoft "
    elif vid == "05AC":
        vendor_hint = "Apple "
    elif vid == "1B1C":
        vendor_hint = "Corsair "
    elif vid == "1532":
        vendor_hint = "Razer "
    elif vid == "0BDA":
        vendor_hint = "Realtek "
    elif vid == "0E8D":
        vendor_hint = "MediaTek "

    is_hid = (
        "HID" in usb_class
        or "CLASS_03" in interfaces_str
        or "HIDCLASS" in usb_class.upper()
    )
    is_mouse = "PROT_02" in interfaces_str or "PROT_2" in interfaces_str
    is_keyboard = "PROT_01" in interfaces_str or "PROT_1" in interfaces_str
    is_mass_storage = "MASS" in usb_class or "CLASS_08" in interfaces_str
    is_hub = "HUB" in usb_class or "CLASS_09" in interfaces_str
    is_video = "VIDEO" in usb_class or "CLASS_0E" in interfaces_str
    is_audio = "AUDIO" in usb_class or "CLASS_01" in interfaces_str
    is_composite = "COMPOSITE" in interfaces_str
    is_vendor_specific = "CLASS_FF" in interfaces_str

    parts = []

    if is_mass_storage:
        parts.append("USB storage drive (flash drive / external disk)")
    elif is_hub:
        parts.append("USB hub")
    elif is_video:
        parts.append("webcam / video device")
    elif is_audio:
        parts.append("audio device (headset / speaker / mic)")
    elif is_hid:
        if is_mouse and is_keyboard:
            parts.append("keyboard + mouse (or combo)")
        elif is_mouse:
            parts.append("mouse / pointing device")
        elif is_keyboard:
            parts.append("keyboard")
        else:
            parts.append("input device (mouse / keyboard / gamepad)")
    elif is_vendor_specific and vid == "0BDA":
        parts.append("vendor-specific device (possible SDR / tuner)")
    else:
        name = get_device_name(device_info).lower()
        if any(x in name for x in ("mouse", "pointing")):
            parts.append("mouse / pointing device")
        elif any(x in name for x in ("keyboard", "kbd")):
            parts.append("keyboard")
        elif any(x in name for x in ("storage", "disk", "flash", "mass")):
            parts.append("storage device")
        elif "hub" in name:
            parts.append("USB hub")
        elif any(x in name for x in ("camera", "webcam", "video")):
            parts.append("webcam")
        elif any(x in name for x in ("sdr", "rtl", "tuner", "dvb")):
            parts.append("SDR / TV tuner")
        else:
            parts.append("USB device")

    summary = vendor_hint + parts[0]

    if is_composite and len(interfaces) > 1:
        summary += " (composite – multiple interfaces)"

    return summary.capitalize()


def format_device_details(device_id: str, device_info: Dict[str, Any]) -> str:
    """Create a multi-line string with key device details."""
    name = get_device_name(device_info)
    vendor = get_vendor_name(device_info)
    serial = device_info.get(ID_SERIAL, "(none)") or "(none)"
    location = get_location(device_id, device_info)
    usb_class = device_info.get(ID_USB_CLASS_FROM_DATABASE, "")
    interfaces = device_info.get(ID_USB_INTERFACES, ())
    likely = get_likely_purpose(device_info)
    readable_ids = get_readable_ids(device_info)

    lines = [
        f"  Likely:   [bold yellow]{likely}[/bold yellow]",
        f"  Location: {location}",
        f"  Device:   {name}",
        f"  Vendor:   {vendor}",
        f"  {readable_ids}",
        f"  Serial:   {serial}",
    ]
    if usb_class:
        lines.append(f"  Class:    {usb_class}")
    if interfaces:
        lines.append(f"  Interfaces: {', '.join(str(i) for i in interfaces)}")
    return "\n".join(lines)


def print_current_devices(monitor: USBMonitor) -> None:
    """Print a nice table of all currently connected USB devices."""
    devices = monitor.get_available_devices()

    if not devices:
        console.print("[yellow]No USB devices currently detected.[/yellow]")
        return

    table = Table(
        title="Currently Connected USB Devices",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title_style="bold green",
    )
    table.add_column("Location / Port", style="dim", overflow="fold", max_width=40)
    table.add_column("Likely / Product", style="yellow")
    table.add_column("Vendor", style="blue")
    table.add_column("VID:PID", style="magenta")

    for device_id, info in sorted(devices.items()):
        location = get_location(device_id, info)
        likely = get_likely_purpose(info)
        vendor = get_vendor_name(info)
        vid_pid = get_vid_pid(info)

        table.add_row(location, likely, vendor, vid_pid)

    console.print(table)
    console.print(f"[dim]{len(devices)} device(s) found[/dim]\n")


def on_connect(device_id: str, device_info: Dict[str, Any]) -> None:
    """Callback when a USB device is plugged in."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = format_device_details(device_id, device_info)
    console.print(
        Panel(
            details,
            title=f"[bold green]CONNECTED[/bold green]  [{timestamp}]",
            border_style="green",
            expand=False,
        )
    )


def on_disconnect(device_id: str, device_info: Dict[str, Any]) -> None:
    """Callback when a USB device is unplugged."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = format_device_details(device_id, device_info)
    console.print(
        Panel(
            details,
            title=f"[bold red]DISCONNECTED[/bold red]  [{timestamp}]",
            border_style="red",
            expand=False,
        )
    )


VERSION = "1.3.0"  # Bump this when identification logic changes

def main() -> None:
    console.print(
        Panel.fit(
            f"[bold cyan]USB Device Inspector[/bold cyan]  [dim]v{VERSION}[/dim]\n"
            "Inspect USB devices and monitor hot-plug events\n"
            "[dim]Local known devices + automatic lookup from official USB ID database[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Pre-load the USB ID database so the first device is identified quickly
    load_usb_ids_database()

    monitor = USBMonitor()

    print_current_devices(monitor)

    console.print("[bold]Monitoring for USB hot-plug events...[/bold] (Ctrl+C to exit)\n")

    monitor.start_monitoring(
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        check_every_seconds=0.5,
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitor...[/yellow]")
        monitor.stop_monitoring()
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    main()
