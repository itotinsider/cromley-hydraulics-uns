I've written the draft report to `reports/RCA-2026-001.md`. The analysis scripts are in `work/`. Pad 3 was really overheating; it was not a false reading. Whether the babbitt is actually damaged can only be confirmed by opening the TGB.

**Problem statement:** On 3 Nov 2026 at 09:00 the CH PLC raised a high-high alarm (85 °C) on Unit 1 TGB pad 3. The shift cut load to 34 MW at 09:14 and stopped the unit in a controlled way at 09:51.

**Roots**
- **Physical (to be confirmed at inspection):** the oil film on pad 3 broke down. Pad 3 is the tightest pad: 0.24 mm against a 0.30 mm design, accepted on a CH concession in 2019. It runs in oil that is 46 months old and oxidised (TAN 0.38, tin 14.2 ppm). It warmed steadily over about 16 days, and the step to about 42 MW for the Unit 2 trial took it to high-high.
- **Human:** the Unit 1 TGB oil change was cancelled under MOC-2025-004, five lab "Caution" results never led to an oil change, the August resample (WO-2026-0672) was deferred with no new date, and the 23:54 high alarm ran for 9 h because the control room cannot see CH PLC alarms.
- **Latent:**
  - The MOC process lets a change go live while the reliability sign-off is conditional or pending. This is the same root as RCA-2025-007, and it is happening again now with MOC-2026-019.
  - The oil sampling and change intervals are longer than Cromley Hydraulics recommends.
  - Nothing turns a lab Caution result into a work order with a due date.
  - The CH PLC pad alarms were never brought into the control room after the retrofit.

**Why I ruled out a faulty sensor:** the extra ~12 K on pad 3 disappeared within about 10 minutes of the stop (pad 3 then read 0.3–0.5 K below its neighbours). A corroded connector would have kept the offset with the unit stopped. In addition, there were no spikes, the neighbouring pads and the oil rose with it, and the two elements on pad 1 agreed within 0.4 K. Cooling, rough zone, water in oil, unbalance and shear pins are also ruled out with data. Shaft misalignment and anything introduced at the October inspection stay open.

**Top three actions**
1. Before any restart: take an oil sample before draining, open the TGB, measure the clearances, and change and flush the oil. Agree with Cromley Hydraulics what to do with pad 3.
2. Bring the CH PLC pad alarms, plus an alarm when a pad is more than 5 K above its neighbours, into the control room. Until then, check the CH viewer every shift.
3. Go back to quarterly TGB oil sampling and a 36-month maximum oil change, make lab Caution results create a work order with a due date, and stop MOCs going live without reliability sign-off.

**Needs a decision now (outside this RCA):** since 06:10 on 3 Nov, Unit 2 has been held at about 55 % gate opening, where Cromley Hydraulics says the vortex rope is strongest. Its turbine guide bearing vibration averaged 93.5 µm on 3 Nov, against about 64 µm on earlier days. It stayed there after Unit 1 stopped, under a bypass that has no reliability sign-off.

**Open questions for the team**
- Is Unit 1 still stopped? If it is still stopped at 09:51 today, downtime passes 24 h, which makes this a Level 2 RCA, not the Level 1 noted in the shift log.
- What did the oil sample requested at 09:14 show?
- Where are concession CH-CON-2019-017 and the 2019 re-babbitting records?
- What did pad 3 read between 12 Sep and 12 Oct? The historian export starts on 13 Oct.
- Was the TGB oil pot touched during the 4–8 Oct annual inspection?
- I've written interview questions for Ray Okafor, Ben Carver and Gina Alvarez, Priya Nandakumar, Dale Whitaker and Nora Fenwick, Marcus Bell, and Karen Doyle and Elena Marsh (section 12 of the report).

I numbered the report RCA-2026-001 because there is no 2026 RCA in the library; please confirm the number.

_38 turns, 6.4 min, USD 2.83_
