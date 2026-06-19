# Point-of-Sale (POS) Troubleshooting Guide

**Contoso Retail — Store Operations**
Effective: January 2026
Owner: Store Systems Support Team
Document version: 3.1

This guide helps store managers and associates diagnose and resolve common point-of-sale (POS) register issues before escalating to the Store Systems Support Team.

---

## Before you start

- Note the **register number** (printed on the label above the cash drawer, format `POS-##`).
- Note the **terminal serial number** (back of the screen, starts with `CTR-`).
- Check whether the issue affects **one register** or **all registers** in the store. An all-register outage is almost always a network or back-office server problem, not a single terminal.

---

## Issue 1 — Register will not power on

1. Confirm the power strip switch under the counter is in the ON position (green light).
2. Reseat the power cable at both the terminal and the wall.
3. Hold the power button for 10 seconds to force a full restart.
4. If the terminal still shows a black screen, swap the power brick with a known-good register and retry.
5. Still dead after a power-brick swap: tag the register **Out of Service**, move the cash drawer to a spare lane, and open a ticket (priority: High).

## Issue 2 — Card reader / chip terminal not responding

Symptoms: "Insert card" prompt missing, frozen "Processing", or declined reads on every card.

1. Check the cable from the PIN pad to the register is fully seated.
2. From the manager menu, choose **Devices > Reset payment terminal**. Wait 60 seconds for it to re-pair.
3. Run a **test transaction** of $0.01 using a store test card, then void it.
4. If chip reads fail but tap (contactless) works, the chip slot likely has debris. Use a cleaning card; do not use liquid.
5. If all read methods fail on one lane but other lanes work, the PIN pad is faulty. Swap in the spare PIN pad from the back office and open a ticket (priority: Medium).

> **Important:** Never key in full card numbers manually to "work around" a broken reader except where the payment screen explicitly offers manual entry. Manual workarounds outside the approved flow are a PCI compliance violation.

## Issue 3 — Receipt printer not printing

1. Open the printer lid and confirm the paper roll is loaded with the paper feeding from underneath.
2. Check for a paper jam and clear any torn pieces.
3. Press the **Feed** button. If paper advances but receipts are blank, the roll is loaded upside down — flip it.
4. If the printer light is blinking red, it is out of paper or the lid is not fully closed.
5. Persistent failure after a paper reload and restart: switch the lane to **email receipt only** mode and open a ticket (priority: Low).

## Issue 4 — "Cannot connect to store server" error

This is a network or back-office issue, not a register fault.

1. Confirm whether **all** registers show the error. If yes, go straight to step 4.
2. On the affected register, choose **Network > Reconnect**.
3. Check the network cable at the back of the terminal is seated (look for the link light on the port).
4. If all registers are offline: restart the back-office network switch (back office, labeled **STORE-SW1**) by unplugging for 30 seconds. Allow 3 minutes for registers to reconnect.
5. If registers stay offline after the switch restart, the store is in a connectivity outage. Switch registers to **Store-and-Forward (offline) mode** so you can keep selling, and open a ticket (priority: Critical).

## Issue 5 — Prices or promotions are wrong at the register

1. Confirm the item's shelf label matches the system by scanning it on the price-check station.
2. If a promotion did not apply, verify the promotion start date and that the customer met the conditions (quantity, member status).
3. Manager override: apply the correct price via **Manager menu > Price override**, and record the reason code.
4. If multiple items show wrong prices, the daily price file may not have synced. Trigger **Back office > Force price file refresh** and recheck.

---

## When to escalate and how

| Situation | Priority | Action |
|---|---|---|
| Whole store cannot process payments | Critical | Phone the support hotline immediately, then open a ticket |
| One lane down during peak hours | High | Open a ticket, move drawer to a spare lane |
| One lane down, store not busy | Medium | Open a ticket, continue on remaining lanes |
| Receipt/printer cosmetic issues | Low | Open a ticket at end of day |

**Store Systems Support hotline:** (555) 200-7788 (open 6 AM – midnight)
**Ticket portal:** storesupport.contoso.com
**After-hours critical outages:** (555) 200-7700 (24/7)

> **Tip:** Always quote the register number and terminal serial when you call. It cuts diagnosis time roughly in half.
