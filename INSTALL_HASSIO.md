# Quick start on Home Assistant (Supervisor / HA OS)

Same steps as the add-on repo; duplicated here so you have one file in each checkout.

Use branch **`dev`** until merged to `main` (set default branch on GitHub or merge `dev` → `main`).

## 1. Add-on Kismet

Repository: `https://github.com/kitsune0n/hassio-kismet-addon`

1. **Settings → Add-ons → Repositories** → add URL above.
2. Install **Kismet Sniffer**, configure `wifi_interfaces`, **Start**, check **Log**.
3. API on host: **2501/tcp** (test from LAN: `http://<HA_LAN_IP>:2501/`).

Requires **monitor mode**-capable Wi‑Fi hardware on the HA host.

## 2. This integration

### HACS

1. **HACS → Custom repositories** → **Integration** → `https://github.com/kitsune0n/ha-kismet-tracker`
2. Download **Kismet Tracker**, **Restart HA**.

### Manual

Copy `custom_components/kismet_tracker` to `/config/custom_components/`, restart.

## 3. UI setup

**Settings → Devices & services → Add integration → Kismet Tracker**

- **Host:** LAN IP of the HA machine (or whatever URL reaches Kismet :2501 from Core). Avoid blind `127.0.0.1` unless you know Docker routing.
- **Port:** `2501`
- **Allow list:** MACs for trackers only

See also the add-on [INSTALL_HASSIO.md](https://github.com/kitsune0n/hassio-kismet-addon/blob/dev/INSTALL_HASSIO.md) in the other repo (identical intent).
