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

Who owns which name, and how a change is made, is in
[`inventory/README.md`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/README.md).
The single source of truth for both topic trees is
[`common/namespace.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/common/namespace.py).

**Stability:** a rename or removal breaks external clients (edge devices, Node-RED, MQTT Explorer
bookmarks, dashboards), so it is always mentioned in the pull request that makes it.
