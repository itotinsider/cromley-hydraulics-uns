---
house: CH
out: supplier/CH-SB-2026-03_Service-Bulletin_RTD-Element-B-Connectors.pdf
title: Service Bulletin CH-SB-2026-03
subtitle: Element-B RTD connectors in humid locations (CH monitoring PLC retrofit)
doc: CH-SB-2026-03
rev: 1
date: 2026-10-06
applies: All FC-40/100 units with the 2026 CH monitoring PLC retrofit, including Copper Canyon Units 1–3
owner: Cromley Hydraulics, Field Service
status: Recommended (not mandatory)
class: Supplier document. Fictional, for training only.
---

## 1 Reason for this bulletin

On early retrofit installations at two sites, individual element-B RTD channels showed a **slow upward drift of up to approx. 20 K** over several hours or days, sometimes with occasional spikes. In every case the bearing itself was healthy. The cause was moisture inside the M12 connector of the element-B extension cable, in junction boxes located in wet areas (headcover pit, lower bracket near the shaft seal). Moisture starts corrosion on the connector contacts, which adds series resistance to the Pt100 loop; the PLC reads the extra resistance as a higher temperature.

The PLC keeps reporting `quality: GOOD` for these channels: the signal path is intact from the PLC's point of view.

## 2 How to recognise it

- One pad temperature changes while the **neighbouring pads, the oil bath and (for pad 1) element A** stay flat.
- No change in the bearing's shaft vibration.
- The affected channel is wired through a junction box in a wet area (typically JB-x-04, headcover pit, which serves the TGB).
- The drift may follow humidity: higher during or after periods of high headcover sump pump activity.

A real bearing problem moves its neighbours and its oil bath too (see CH-DOC-OM-0101 section 8.1). One channel moving alone is a measurement fault until proven otherwise.

## 3 Recommended actions

1. **Do not stop the unit on an element-B pad alarm alone** if the cross-checks in section 2 show no corroborating signal. Follow the owner's bearing alarm validation procedure.
2. At the next opportunity, open the junction box, inspect the M12 connector for moisture or corrosion, dry it, replace the connector seal and **tighten the cable gland to the specified torque**.
3. Measure loop resistance and insulation resistance (above 20 MΩ at 100 V).
4. Re-check all element-B glands in wet areas every 6 months (added to CH-DOC-OM-0101 Rev 4, chapter 10).
5. Consider a plausibility check in the owner's analytics: flag any pad deviating more than 5 K from its neighbours without a matching oil bath change.

## 4 Parts

| Part | CH part no. |
| --- | --- |
| M12 connector seal kit (10 pcs) | CH-PLC-M12-SK10 |
| Cable gland M20, IP68, with seal insert | CH-PLC-GL-M20 |

Contact Cromley Hydraulics Field Service (Lars Bergström for Copper Canyon Dam) for support.
