# Kismet Tracker (Home Assistant)

Custom integration that polls a local [Kismet](https://www.kismetwireless.net/) REST API and exposes **device_tracker** entities **only for MAC addresses you allow-list**. Optional sensors report how many devices Kismet saw recently (RF “busyness” proxy).

Pair this with the Supervisor add-on **hassio-kismet-addon** (add-on directory `kismet/`) or any Kismet instance reachable from Home Assistant.

## Features

- Config Flow: host, port, TLS options, optional HTTP basic auth, polling interval.
- **Whitelist-only** device trackers (no entity spam for every observed station).
- Ignores **locally administered / randomized-looking MACs** in the allow list when enabled.
- **Away** timeout from Kismet `last_time` plus optional **minimum RSSI** for `home` (`-200` disables the RSSI gate).
- **BLE**: allow-list public BLE MACs the same way; `source_type` switches when Kismet marks Bluetooth PHY hints.
- Optional **recent RF device count** sensor (`/devices/last-time/...`) with configurable window.

## Install (manual)

Copy `custom_components/kismet_tracker` into your Home Assistant `config/custom_components/` directory, restart, then add the integration from **Settings → Devices & services**.

## Install (HACS)

1. **HACS → ⋮ → Custom repositories** → Category **Integration** → add this repository URL.
2. Install **Kismet Tracker** and restart Home Assistant.
3. Configure the integration UI.

## Kismet API

Uses efficient whitelist polling via `POST /devices/multimac/devices.json` and a lightweight `GET /devices/last-time/-1/devices.json` connectivity check.

## Soak testing checklist

Use this when validating long runs:

- Confirm stable memory on the Kismet host and on Home Assistant over 24–72 h.
- Try polling intervals 15–60 s; watch Kismet CPU and HA log for `UpdateFailed` spikes.
- Toggle **enable air sensors** and verify extra JSON load is acceptable on weak hardware.
- With **minimum RSSI**, walk test devices through edge RSSI to ensure `home`/`not_home` matches expectations.
- After changing the allow list in **Options**, the entry reloads; stale `device_tracker` orphans should disappear from the entity registry on reload (restart if needed).

## What to provide when reporting issues

Home Assistant Core and Supervisor versions, architecture, how Kismet runs (add-on vs external), adapter chipset / monitor-mode capability, redacted allow list size (not necessarily the MACs), and relevant logs from **Kismet** and **`kismet_tracker`**.
