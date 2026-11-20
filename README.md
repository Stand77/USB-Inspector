# USB Device Inspector

Inspect USB devices on your PC and watch for hot-plug events in real time.

Identifies devices by name when possible (Logitech keyboards, RTL-SDR receivers, Spectrum Interlink controllers, MediaTek preloader / Alexa boot mode, and many more), shows port/location info, VID:PID with human-readable names, serial numbers, and a short "Likely" purpose summary.

**Version:** 1.3.0

---

## Download Windows executable (no Python required)

| File | Description |
|------|-------------|
| [**USBInspector.exe**](https://github.com/Stand77/USB-Inspector/releases/download/v1.3.0/USBInspector.exe) | Standalone Windows app (~10 MB) |

**Release page:** [v1.3.0](https://github.com/Stand77/USB-Inspector/releases/tag/v1.3.0)

1. Click the link above to download.
2. Save the file somewhere convenient.
3. Double-click to run. Windows may show a SmartScreen warning the first time — choose **More info** → **Run anyway** (this is normal for unsigned apps).

No Python install is needed for the `.exe`.

---

## Features

- Lists currently connected USB devices with clear names and locations
- Real-time **hot-plug** monitoring (connect / disconnect panels)
- **Likely** purpose summary (mouse, keyboard, SDR, flight controller, etc.)
- Human-readable Vendor / Device ID text when known
- Automatic lookup from the official [usb.ids](http://www.linux-usb.org/usb.ids) database (cached after first run)
- Windows **Port_# / Hub_#** location info when available
- Curated entries for common devices (Logitech, Realtek RTL-SDR, Spectrum Interlink DX, MediaTek preloader, etc.)

---

## Run from source (Python)

```bash
# Clone
git clone https://github.com/Stand77/USB-Inspector.git
cd USB-Inspector

# Virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Run
python usb_inspector.py
```

**Windows note:** `usb-monitor` pulls in `pywin32` and `wmi` automatically.

**Linux note:** You may need:

```bash
sudo apt install python3-dev libudev-dev
```

---

## Build your own Windows .exe

On a Windows machine with Python 3.9+ (or 3.10+):

```cmd
pip install -r requirements.txt pyinstaller
py -3.9 -m PyInstaller --onefile --name USBInspector usb_inspector.py
```

The executable appears in `dist\USBInspector.exe`.

---

## Publishing a new version (for maintainers)

1. Build a fresh `USBInspector.exe` on Windows.
2. On GitHub: **Releases** → **Draft a new release**.
3. Tag e.g. `v1.4.0`, title e.g. `USB Inspector v1.4.0`.
4. Upload `USBInspector.exe` as a release asset.
5. Publish, then update the download link in this README to the new tag.

---

## How it works

Uses the cross-platform [usb-monitor](https://pypi.org/project/usb-monitor/) library:

- **Windows:** WMI
- **Linux:** pyudev
- **macOS:** I/O Registry

Identification order:

1. Local curated VID:PID list  
2. Official `usb.ids` database (downloaded once and cached)  
3. Class / interface heuristics (HID mouse/keyboard, mass storage, etc.)

---

## Limitations

- Physical port numbers are approximate; nested hubs show as `Port_#xxxx.Hub_#yyyy` when Windows provides that info.
- Some devices only appear briefly (e.g. MediaTek PreLoader during boot) or not at all when fully booted if they only use USB for power.
- Windows SmartScreen may warn about unsigned executables.
- Elevated privileges may be needed on some systems to see every device.

---

## License

MIT — see [LICENSE](LICENSE).
