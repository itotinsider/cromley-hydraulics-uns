# Configuration

Settings are environment variables in
[`docker-compose.yml`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/docker-compose.yml).
Each has a default in the code. After a change: `docker compose up -d --build`.

## All services

| Variable | Default | Purpose |
|---|---|---|
| `MQTT_HOST` / `MQTT_PORT` | `mosquitto` / `1883` | The broker, by compose service name (never localhost inside a container) |
| `WEB_PORT` | per service | HTTP port inside the container: 8120 SCADA, 8121 instructor, 8122 viewer, 8123 dam-sim, 8125 ch-plc-sim |

## dam-sim

| Variable | Default | Purpose |
|---|---|---|
| `PUBLISH_INTERVAL_SECONDS` | `1` | Customer tree publish period |
| `STEP_SECONDS` | `0.1` | Physics step |
| `HARDWIRED_URL` | `http://ch-plc-sim:8125/api/hardwired` | Where the dam reads the customer's turbine sensors (the "copper") |
| `START_LEVEL_M` | `412` | Reservoir level at start, m a.s.l. |
| `INFLOW_M3S` | `115` | Mean river inflow |
| `PLANT_MW_SETPOINT` | `110` | The grid operator's setpoint at start |
| `AGC_ENABLED` | `true` | AGC offset of up to ±5 MW |
| `SEED` | `1` | Random seed (inflow, AGC, frequency, noise) |

## ch-plc-sim

| Variable | Default | Purpose |
|---|---|---|
| `PUBLISH_INTERVAL_SECONDS` | `1` | Process value period |
| `DATA_DIR` | `/app/data` | Where the counters are kept (`data/ch_plc_counters.json` on the host) |
| `COOLING_WATER_TEMP_C` | `14` | Mean cooling water temperature (season); ±0.8 °C daily |
| `RETAIN_PROCESS_VALUES` | `true` | Retain the 1 s process values |
| `DETAILED_TURBINES` | `3` | How many turbines (Unit1 first) publish waveforms, 0–3 |
| `WAVEFORM_SHAFT_EVERY_S` / `_SECONDS` | `30` / `4` | 6 shaft displacement channels at 1 kS/s |
| `WAVEFORM_DRAFTTUBE_EVERY_S` / `_SECONDS` | `30` / `10` | Draft-tube pressure at 100 S/s |
| `WAVEFORM_ACCEL_EVERY_S` / `_SECONDS` | `300` / `0.5` | Headcover accelerometer at 10 kS/s |

## dam-scada

| Variable | Default | Purpose |
|---|---|---|
| `STALE_SECONDS` | `5` | A value older than this is bad quality and not alarmed |
| `PUBLIC_INSTRUCTOR_URL`, `PUBLIC_VIEWER_URL`, `PUBLIC_NODERED_URL`, `PUBLIC_MQTT_EXPLORER_URL`, `PUBLIC_BROKER` | localhost URLs from the host ports | Links shown on the hub page |
| `PUBLIC_WIKI_URL` | the GitHub wiki | Link on the hub |

## instructor, ch-viewer, nodered, mqtt-explorer

| Variable | Default | Purpose |
|---|---|---|
| `DAM_URL` / `CH_URL` | `http://dam-sim:8123` / `http://ch-plc-sim:8125` | Instructor → simulators (HTTP, compose network) |
| `PUBLIC_HUB_URL` | `http://localhost:8120` | "All systems" link on the instructor station and the viewer |
| `FLOWS` | `flows.json` | Pins Node-RED's flow file name |
| `BEARING_CSV_FILE` | `/data/exports/ch_bearings_1min.csv` | Where the Node-RED bearing flow appends rows (`exports/` on the host) |
| `HTTP_PORT` | `4000` | MQTT Explorer's web port inside the container |

## Several stacks on one machine

One stack per git worktree or agent: put a git-ignored `.env` file next to `docker-compose.yml`.
Compose reads it automatically. Container names and image tags then carry the stack name; inside
the network the services keep their standard ports.

| Variable | Default | |
|---|---|---|
| `CH_STACK` | `ch` | Prefix of container names and image tags |
| `CH_HUB_PORT` | `8120` | Hub + dam SCADA |
| `CH_INSTRUCTOR_PORT` | `8121` | Instructor station |
| `CH_VIEWER_PORT` | `8122` | CH asset viewer |
| `CH_MQTT_PORT` | `1884` | Mosquitto |
| `CH_NODERED_PORT` | `1881` | Node-RED |
| `CH_MQTT_EXPLORER_PORT` | `4001` | MQTT Explorer |

```bash
# .env
CH_STACK=ch2
CH_HUB_PORT=8220
CH_INSTRUCTOR_PORT=8221
CH_VIEWER_PORT=8222
CH_MQTT_PORT=1984
CH_NODERED_PORT=1981
CH_MQTT_EXPLORER_PORT=4101
```
