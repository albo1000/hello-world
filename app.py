import asyncio
import threading
import time
from flask import Flask, jsonify, render_template
from bleak import BleakScanner

app = Flask(__name__)

# Shared state
_scan_results = []
_scan_lock = threading.Lock()
_scanning = False


async def _run_scan(duration: float = 5.0):
    devices = await BleakScanner.discover(timeout=duration, return_adv=True)
    results = []
    for addr, (device, adv) in devices.items():
        results.append({
            "address": addr,
            "name": device.name or "Unknown",
            "rssi": adv.rssi,
            "signal": _rssi_to_label(adv.rssi),
        })
    results.sort(key=lambda d: d["rssi"], reverse=True)
    return results


def _rssi_to_label(rssi):
    if rssi is None:
        return "Unknown"
    if rssi >= -60:
        return "Strong"
    if rssi >= -75:
        return "Good"
    if rssi >= -90:
        return "Weak"
    return "Very Weak"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan")
def scan():
    global _scan_results, _scanning
    with _scan_lock:
        if _scanning:
            return jsonify({"status": "scanning", "devices": _scan_results})

        _scanning = True

    def run():
        global _scan_results, _scanning
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(_run_scan(5.0))
            with _scan_lock:
                _scan_results = results
        except Exception as e:
            with _scan_lock:
                _scan_results = []
            print(f"Scan error: {e}")
        finally:
            loop.close()
            with _scan_lock:
                _scanning = False

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return jsonify({"status": "started", "devices": _scan_results})


@app.route("/results")
def results():
    with _scan_lock:
        return jsonify({
            "status": "scanning" if _scanning else "idle",
            "devices": _scan_results,
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
