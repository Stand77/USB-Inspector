# USB Device Inspector

A Python application that inspects currently connected USB devices and monitors for hot-plug events (devices being plugged in or unplugged).

It identifies devices by name (e.g., Logitech Wireless Keyboard, RTL-SDR Receiver, ANT+ dongle, etc.), shows location/port information where available, vendor/product IDs, serial numbers, and more.

## Features

- Lists all currently connected USB devices with detailed information
- Real-time monitoring of device insertion and removal (hot-plugging)
- Cross-platform support (Linux, Windows, macOS) via the `usb-monitor` library
- Clean, colored terminal output using Rich
- Shows useful identifiers:
  - Device model / product name
  - Vendor name
  - VID:PID
  - Serial number (when available)
  - Location / path (e.g. `/dev/bus/usb/...` on Linux, device ID on Windows)
  - USB interfaces

## Installation

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Note on Linux:** You may need additional system packages for full USB access:
```bash
sudo apt install python3-dev libudev-dev   # Debian/Ubuntu
# or equivalent on other distros
```

**Note on Windows:** The `usb-monitor` library uses `pywin32` and `wmi`, which are installed automatically.

## Usage

```bash
python usb_inspector.py
```

The app will:
1. Print a table of all currently connected USB devices
2. Start monitoring for hot-plug events
3. Print clear messages when devices are plugged in or unplugged
4. Run until you press `Ctrl+C`

### Example Output

```
Currently Connected USB Devices
┌─────────────────────────────────────────────────────────────┬──────────────────────────┬──────────┬─────────────────────┐
│ Location                                                    │ Device                   │ VID:PID  │ Vendor              │
├─────────────────────────────────────────────────────────────┼──────────────────────────┼──────────┼─────────────────────┤
│ /dev/bus/usb/001/003                                        │ Logitech USB Receiver    │ 046d:c52b│ Logitech, Inc.      │
│ /dev/bus/usb/001/004                                        │ RTL2832U                 │ 0bda:2838│ Realtek             │
└─────────────────────────────────────────────────────────────┴──────────────────────────┴──────────┴─────────────────────┘

Monitoring for USB hot-plug events... (Ctrl+C to exit)

[2026-10-23 12:05:12] CONNECTED
  Location: /dev/bus/usb/001/005
  Device:   Wireless Mouse
  VID:PID:  046d:c077
  Vendor:   Logitech, Inc.
  Serial:   (none)

[2026-10-23 12:05:45] DISCONNECTED
  Location: /dev/bus/usb/001/005
  Device:   Wireless Mouse
  ...
```

## How It Works

The application uses the excellent cross-platform [`usb-monitor`](https://pypi.org/project/usb-monitor/) library, which:

- Uses **pyudev** on Linux
- Uses **WMI** on Windows
- Uses the I/O Registry on macOS

It normalizes device attributes across platforms so the same code works everywhere.

The "Location" field uses the device path/ID provided by the underlying system (closest practical equivalent to a USB port number across platforms).

## Limitations

- Physical port numbers (e.g. "Port 3 on Hub 2") are not always directly available in a consistent cross-platform way. The location path is the best portable identifier.
- Some devices may not report a friendly product name; in those cases VID:PID is shown.
- Root hubs and internal USB controllers are also listed.
- On some systems, elevated privileges may be required to see all devices.

## Extending

You can easily modify `usb_inspector.py` to:
- Filter for specific VID/PID pairs
- Trigger actions when particular devices are plugged in
- Export events to a log file or JSON
- Add a GUI with tkinter or a web interface

## License

MIT
