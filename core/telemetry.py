"""
AizenOS Universal Cross-Platform Telemetry & Hardware Monitor.
Supports macOS (Darwin), Linux OS, and Windows seamlessly.
"""

import platform
import subprocess
import shutil
import re
import os

IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

def get_battery_info() -> str:
    """Returns real-time battery percentage, charging state, and power source across macOS, Linux, and Windows."""
    if IS_MAC:
        try:
            out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
            pct = re.search(r"(\d+%)", out)
            status = re.search(r";\s*([^;]+);", out)
            rem = re.search(r";\s*(\d+:\d+\s+remaining)", out)
            pct_str = pct.group(1) if pct else "Unknown"
            status_str = status.group(1).strip() if status else "discharging"
            rem_str = rem.group(1).strip() if rem else ""
            power_source = "AC Power" if "AC Power" in out else "Battery Power"
            details = f"{pct_str} ({status_str} on {power_source}"
            if rem_str:
                details += f", ~{rem_str}"
            details += ")"
            return f"🔋 Battery: {details}"
        except Exception as e:
            return f"Could not read battery status: {e}"
    elif IS_LINUX:
        bat_dirs = ["/sys/class/power_supply/BAT0", "/sys/class/power_supply/BAT1"]
        for b_dir in bat_dirs:
            cap_file = os.path.join(b_dir, "capacity")
            status_file = os.path.join(b_dir, "status")
            if os.path.isfile(cap_file):
                try:
                    with open(cap_file) as f:
                        pct = f.read().strip()
                    status = "discharging"
                    if os.path.isfile(status_file):
                        with open(status_file) as f:
                            status = f.read().strip().lower()
                    return f"🔋 Battery: {pct}% ({status})"
                except Exception:
                    pass
        try:
            out = subprocess.check_output(["acpi", "-b"], text=True).strip()
            return f"🔋 Battery: {out}"
        except Exception:
            return "🔋 Battery: AC Connected (No battery detected / Desktop)"
    elif IS_WINDOWS:
        try:
            ps_cmd = "(Get-CimInstance Win32_Battery | Select-Object -First 1 -Property EstimatedChargeRemaining, BatteryStatus) | ConvertTo-Json"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True).strip()
            import json
            data = json.loads(out)
            pct = data.get("EstimatedChargeRemaining", "Unknown")
            status_code = data.get("BatteryStatus", 1)
            # 1: Discharging, 2: AC/Charging, 3: Fully Charged
            status_map = {1: "discharging", 2: "charging", 3: "fully charged"}
            status_str = status_map.get(status_code, "on battery")
            return f"🔋 Battery: {pct}% ({status_str})"
        except Exception:
            return "🔋 Battery: AC Connected / Desktop (Windows)"
    return "🔋 Battery: Platform unsupported"

def get_wifi_info() -> str:
    """Returns current Wi-Fi network SSID and connection state across macOS, Linux, and Windows."""
    if IS_MAC:
        try:
            out = subprocess.check_output(["networksetup", "-getairportnetwork", "en0"], text=True).strip()
            if "not associated" in out.lower():
                return "📶 Wi-Fi: Disconnected (Not associated with any network)"
            return f"📶 {out}"
        except Exception as e:
            return f"📶 Wi-Fi: Status check unavailable ({e})"
    elif IS_LINUX:
        try:
            out = subprocess.check_output(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], text=True).strip()
            for line in out.splitlines():
                if line.startswith("yes:"):
                    return f"📶 Wi-Fi: Connected to '{line.split(':', 1)[1]}'"
            return "📶 Wi-Fi: Disconnected"
        except Exception:
            try:
                out = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
                if out:
                    return f"📶 Wi-Fi: Connected to '{out}'"
            except Exception:
                pass
            return "📶 Wi-Fi: Disconnected or nmcli not installed"
    elif IS_WINDOWS:
        try:
            out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True)
            ssid_m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
            state_m = re.search(r"^\s*State\s*:\s*(.+)$", out, re.MULTILINE)
            if ssid_m and state_m and "connected" in state_m.group(1).lower():
                return f"📶 Wi-Fi: Connected to '{ssid_m.group(1).strip()}'"
            return "📶 Wi-Fi: Disconnected (Windows WLAN)"
        except Exception:
            return "📶 Wi-Fi: Wired or unavailable (Windows)"
    return "📶 Wi-Fi: Platform unsupported"

def get_system_vitals() -> dict:
    """Returns disk, ram, battery, and platform vitals across macOS, Linux, and Windows."""
    target_root = "C:\\" if IS_WINDOWS else "/"
    total, used, free = shutil.disk_usage(target_root)
    free_gb = free / (1024 ** 3)
    total_gb = total / (1024 ** 3)

    free_ram_gb = 4.0
    if IS_MAC:
        try:
            vm = subprocess.check_output(["vm_stat"], text=True)
            page_size = 16384
            m = re.search(r"page size of (\d+) bytes", vm)
            if m:
                page_size = int(m.group(1))

            pages = {}
            for line in vm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    v_clean = v.strip().rstrip(".")
                    if v_clean.isdigit():
                        pages[k.strip()] = int(v_clean)

            avail = pages.get("Pages free", 0) + pages.get("Pages speculative", 0) + pages.get("Pages inactive", 0) + pages.get("Pages purgeable", 0)
            free_ram_gb = (avail * page_size) / (1024 ** 3)
        except Exception:
            pass
    elif IS_LINUX:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        free_ram_gb = int(line.split()[1]) / (1024 ** 2)
                        break
        except Exception:
            pass
    elif IS_WINDOWS:
        try:
            ps_cmd = "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True).strip()
            free_ram_gb = int(out) / (1024 ** 2)
        except Exception:
            pass

    return {
        "os": "macOS" if IS_MAC else ("Linux" if IS_LINUX else ("Windows" if IS_WINDOWS else platform.system())),
        "arch": platform.machine(),
        "free_disk_gb": round(free_gb, 1),
        "total_disk_gb": round(total_gb, 1),
        "free_ram_gb": round(free_ram_gb, 1),
        "battery": get_battery_info(),
        "wifi": get_wifi_info()
    }
