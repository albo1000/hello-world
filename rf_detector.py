#!/usr/bin/env python3
"""
RF Signal Detector — scans for nearby WiFi and Bluetooth RF signals.

Usage:
  python rf_detector.py             # single scan
  python rf_detector.py --live      # live auto-refresh
  python rf_detector.py --live -r 5 # live, refresh every 5s
"""

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None


# ---------------------------------------------------------------------------
# WiFi scanning
# ---------------------------------------------------------------------------

def scan_wifi_nmcli():
    """Return (list[dict], error_str|None) using nmcli."""
    networks = []
    try:
        result = subprocess.run(
            [
                "nmcli", "-t",
                "-f", "SSID,BSSID,MODE,CHAN,FREQ,RATE,SIGNAL,SECURITY,ACTIVE",
                "dev", "wifi", "list", "--rescan", "yes",
            ],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return networks, result.stderr.strip() or "nmcli returned non-zero"

        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            # nmcli escapes literal colons as \:
            parts = re.split(r'(?<!\\):', line)
            parts = [p.replace("\\:", ":") for p in parts]
            if len(parts) < 9:
                continue

            ssid, bssid, mode, channel, freq, rate, signal_raw, security, active_raw = parts[:9]
            ssid = ssid or "<hidden>"
            signal_pct = int(signal_raw) if signal_raw.isdigit() else 0
            signal_dbm = (signal_pct / 2) - 100
            band = "5 GHz" if freq.startswith("5") else "2.4 GHz"

            networks.append(
                dict(
                    ssid=ssid,
                    bssid=bssid,
                    channel=channel,
                    freq=freq,
                    band=band,
                    signal_pct=signal_pct,
                    signal_dbm=round(signal_dbm),
                    rate=rate,
                    security=security or "Open",
                    active=active_raw.strip() == "yes",
                )
            )
    except FileNotFoundError:
        return networks, "nmcli not found — install NetworkManager."
    except subprocess.TimeoutExpired:
        return networks, "WiFi scan timed out."
    except Exception as exc:
        return networks, str(exc)

    networks.sort(key=lambda n: n["signal_pct"], reverse=True)
    return networks, None


def scan_wifi_iwlist():
    """Fallback WiFi scan using iwlist."""
    networks = []
    try:
        iw = subprocess.run(["iwconfig"], capture_output=True, text=True)
        interfaces = re.findall(r"^(\w+)\s+IEEE", iw.stdout, re.MULTILINE)
        if not interfaces:
            return networks, "No wireless interfaces found."
        iface = interfaces[0]

        result = subprocess.run(
            ["sudo", "iwlist", iface, "scan"],
            capture_output=True, text=True, timeout=20,
        )
        for cell in result.stdout.split("Cell ")[1:]:
            ssid_m = re.search(r'ESSID:"([^"]*)"', cell)
            addr_m = re.search(r"Address: ([0-9A-Fa-f:]+)", cell)
            sig_m = re.search(r"Signal level=(-?\d+) dBm", cell)
            chan_m = re.search(r"Channel:(\d+)", cell)
            freq_m = re.search(r"Frequency:([0-9.]+) GHz", cell)
            enc_m = re.search(r"Encryption key:(on|off)", cell)

            if not (ssid_m and addr_m):
                continue

            ssid = ssid_m.group(1) or "<hidden>"
            signal_dbm = int(sig_m.group(1)) if sig_m else -90
            signal_pct = max(0, min(100, 2 * (signal_dbm + 100)))
            freq_val = float(freq_m.group(1)) if freq_m else 2.4
            band = "5 GHz" if freq_val > 3 else "2.4 GHz"

            networks.append(
                dict(
                    ssid=ssid,
                    bssid=addr_m.group(1),
                    channel=chan_m.group(1) if chan_m else "?",
                    freq=f"{freq_val} GHz",
                    band=band,
                    signal_pct=signal_pct,
                    signal_dbm=signal_dbm,
                    rate="?",
                    security="Encrypted" if enc_m and enc_m.group(1) == "on" else "Open",
                    active=False,
                )
            )
    except Exception as exc:
        return networks, str(exc)

    networks.sort(key=lambda n: n["signal_pct"], reverse=True)
    return networks, None


def get_wifi():
    """Try nmcli first, fall back to iwlist."""
    nets, err = scan_wifi_nmcli()
    if not nets:
        nets, err2 = scan_wifi_iwlist()
        if not nets:
            return [], err or err2
    return nets, None


# ---------------------------------------------------------------------------
# Bluetooth scanning
# ---------------------------------------------------------------------------

def scan_bluetooth():
    """Return list[dict] of nearby Bluetooth devices (best-effort)."""
    devices = {}

    # Prefer bluetoothctl cached devices (fast, no root needed)
    try:
        r = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=5,
        )
        for line in r.stdout.splitlines():
            m = re.match(r"Device ([0-9A-Fa-f:]+) (.+)", line)
            if m:
                devices[m.group(1)] = dict(address=m.group(1), name=m.group(2), type="BT/BLE")
    except Exception:
        pass

    # hcitool for classic scan (may need a moment to discover)
    try:
        r = subprocess.run(
            ["hcitool", "scan", "--flush"],
            capture_output=True, text=True, timeout=12,
        )
        for line in r.stdout.splitlines()[1:]:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0] not in devices:
                devices[parts[0]] = dict(address=parts[0], name=parts[1], type="Classic")
    except Exception:
        pass

    return list(devices.values())


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _signal_markup(signal_pct: int) -> tuple[str, str]:
    """Return (bar_markup, color)."""
    if signal_pct >= 80:
        return "[green]▂▄▆█[/green]", "green"
    if signal_pct >= 60:
        return "[green]▂▄▆ [/green]", "green"
    if signal_pct >= 40:
        return "[yellow]▂▄  [/yellow]", "yellow"
    if signal_pct >= 20:
        return "[orange1]▂   [/orange1]", "orange1"
    return "[red]▂   [/red]", "red"


def build_wifi_table(networks: list) -> "Table":
    table = Table(
        title=f"[bold cyan]WiFi Networks[/bold cyan]  ({len(networks)} found)",
        box=box.ROUNDED,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("SSID", style="cyan", min_width=18)
    table.add_column("Signal", justify="center", min_width=8)
    table.add_column("%", justify="right", min_width=5)
    table.add_column("dBm", justify="right", min_width=6)
    table.add_column("Band", justify="center", min_width=8)
    table.add_column("Ch", justify="center", min_width=4)
    table.add_column("Security", justify="center", min_width=10)
    table.add_column("BSSID", style="dim", min_width=17)

    for net in networks:
        bars, color = _signal_markup(net["signal_pct"])
        ssid_text = (
            f"[bold green]★ {net['ssid']}[/bold green]"
            if net.get("active")
            else net["ssid"]
        )
        band_color = "blue" if "5" in net["band"] else "cyan"
        table.add_row(
            ssid_text,
            bars,
            f"[{color}]{net['signal_pct']}[/{color}]",
            f"[{color}]{net['signal_dbm']}[/{color}]",
            f"[{band_color}]{net['band']}[/{band_color}]",
            net["channel"],
            net["security"],
            net["bssid"],
        )
    return table


def build_bt_table(devices: list) -> "Table":
    table = Table(
        title=f"[bold cyan]Bluetooth Devices[/bold cyan]  ({len(devices)} found)",
        box=box.ROUNDED,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Name", style="cyan")
    table.add_column("Address", style="dim")
    table.add_column("Type", justify="center")
    for dev in devices:
        table.add_row(dev["name"], dev["address"], dev["type"])
    return table


# ---------------------------------------------------------------------------
# Plain-text fallback (no rich)
# ---------------------------------------------------------------------------

def print_plain(networks, bt_devices):
    print("\n=== WiFi Networks ===")
    if networks:
        print(f"{'SSID':<30} {'%':>5} {'dBm':>6} {'Band':>8} {'Ch':>4}  Security")
        print("-" * 68)
        for n in networks:
            print(
                f"{n['ssid']:<30} {n['signal_pct']:>4}% {n['signal_dbm']:>5}dBm"
                f" {n['band']:>8} {n['channel']:>4}  {n['security']}"
            )
    else:
        print("No WiFi networks found.")

    print("\n=== Bluetooth Devices ===")
    if bt_devices:
        for d in bt_devices:
            print(f"  {d['name']}  ({d['address']})  [{d['type']}]")
    else:
        print("No Bluetooth devices found.")


# ---------------------------------------------------------------------------
# Scan runners
# ---------------------------------------------------------------------------

def run_once():
    if HAS_RICH:
        console.print(
            Panel(
                "[bold cyan]RF Signal Detector[/bold cyan]\n"
                "[dim]Scanning WiFi and Bluetooth...[/dim]",
                border_style="cyan",
            )
        )

    with (console.status("[cyan]Scanning WiFi…[/cyan]", spinner="dots") if HAS_RICH
          else _null_ctx()):
        wifi, wifi_err = get_wifi()

    with (console.status("[cyan]Scanning Bluetooth…[/cyan]", spinner="dots") if HAS_RICH
          else _null_ctx()):
        bt = scan_bluetooth()

    if HAS_RICH:
        console.print()
        if wifi:
            console.print(build_wifi_table(wifi))
        else:
            console.print(f"[red]WiFi:[/red] {wifi_err or 'No networks found'}")

        console.print()
        if bt:
            console.print(build_bt_table(bt))
        else:
            console.print("[dim]Bluetooth: no devices found (or adapter unavailable)[/dim]")

        console.print(
            f"\n[dim]Scan completed {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
        )
    else:
        print_plain(wifi, bt)
        print(f"\nScan completed {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def run_live(refresh: int):
    if not HAS_RICH:
        print("Live mode requires the 'rich' package: pip install rich")
        sys.exit(1)

    console.print(
        Panel(
            f"[bold cyan]RF Signal Detector — Live Mode[/bold cyan]\n"
            f"[dim]Refreshing every {refresh}s  |  Ctrl+C to exit[/dim]",
            border_style="cyan",
        )
    )

    try:
        while True:
            wifi, wifi_err = get_wifi()
            bt = scan_bluetooth()

            console.clear()
            console.print(
                Panel(
                    f"[bold cyan]RF Signal Detector[/bold cyan]  "
                    f"[dim]{datetime.now().strftime('%H:%M:%S')}  |  "
                    f"next refresh in {refresh}s  |  Ctrl+C to exit[/dim]",
                    border_style="cyan",
                )
            )

            if wifi:
                console.print(build_wifi_table(wifi))
            else:
                console.print(f"[red]WiFi:[/red] {wifi_err or 'No networks found'}")

            console.print()

            if bt:
                console.print(build_bt_table(bt))
            else:
                console.print("[dim]Bluetooth: no devices found[/dim]")

            time.sleep(refresh)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


class _null_ctx:
    """No-op context manager used when rich is absent."""
    def __enter__(self): return self
    def __exit__(self, *_): pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Detect RF signals (WiFi + Bluetooth) around you.",
        epilog=(
            "Examples:\n"
            "  python rf_detector.py\n"
            "  python rf_detector.py --live\n"
            "  python rf_detector.py --live -r 5\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--live", "-l", action="store_true",
                        help="Continuously refresh the display")
    parser.add_argument("--refresh", "-r", type=int, default=10, metavar="SEC",
                        help="Refresh interval in seconds for live mode (default: 10)")
    args = parser.parse_args()

    if not HAS_RICH:
        print("Tip: pip install rich  — for a much nicer display\n")

    if args.live:
        run_live(args.refresh)
    else:
        run_once()


if __name__ == "__main__":
    main()
