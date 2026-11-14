# Interface reference

Every name one part of Copper Canyon exposes to another is listed in the **interface inventory**,
the [`inventory/`](https://github.com/itotinsider/cromley-hydraulics-uns/tree/main/inventory)
folder in the repository. It is generated from the code and checked by the tests, so you can trust
it.

| File | Contains |
|---|---|
| [`topics.csv`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/topics.csv) | **Start here.** One row per concrete topic, both trees: tree, topic, unit, type, retained, publisher, subscribers, description |
| [`customer.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/customer.json) | The customer tree: every measured tag with unit, type, range, decimals |
| [`ch.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/ch.json) | The CH tree per asset: process tags, waveform channels, events, nameplate, status, context mapping |
| [`commands.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/commands.json) | Every `Cmd` topic, its payload type and range |
| [`hardwired.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/hardwired.json) | The dual-element sensors: customer tag ↔ CH element |
| [`scenarios.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/scenarios.json) | Instructor scenarios of both simulators (instructor only) |
| [`api.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/api.json) | The HTTP routes and response shapes of every service |
| [`interface.json`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/interface.json) | The interface version and a fingerprint of the files above |

Who owns which name, and how a change is made, is in
[`inventory/README.md`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/README.md).
The single source of truth for both topic trees is
[`common/namespace.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/common/namespace.py).

**Stability:** a rename or removal breaks external clients (edge devices, Node-RED, MQTT Explorer
bookmarks, dashboards), so it is always mentioned in the pull request that makes it.

## Building on Copper Canyon from another project

Another project (a course lab, a vendor demo, an analytics stack) can run Copper Canyon unchanged
and add its own containers around it. The inventory is the contract between the two.

1. **Pin a commit.** Build the images from that commit; do not copy the source. Your own compose
   file decides which services run. The minimum plant is `mosquitto`, `dam-sim` and `ch-plc-sim`;
   add `dam-scada` for the operator's screen.
2. **Record the interface version** you built against: `version` in `interface.json`.
3. **Use only what the inventory lists:**
   - data: the topics in `topics.csv`, with the payloads described in `customer.json` and `ch.json`;
   - commands: the topics in `commands.json`;
   - faults: the scenario routes of `dam-sim` and `ch-plc-sim` in `api.json` (list, start, stop,
     ground truth) and the scenario ids in `scenarios.json`. These two services are not exposed on
     the host, so reach them on the compose network;
   - settings: the environment variables on the [Configuration](Configuration) page.
4. **To take in a newer Copper Canyon**, move the pin and compare `interface.json`:
   - same version: nothing you read has changed;
   - second number up: there is something new to use, nothing to fix;
   - first number up: read the pull request that raised it, it names every rename and removal.

What your project needs changed inside Copper Canyon comes here as a pull request, so every user
gets it and the inventory stays the one place where the interface is written down.
