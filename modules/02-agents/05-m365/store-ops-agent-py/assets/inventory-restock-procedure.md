# Inventory Restock Procedure

**Contoso Retail — Store Operations**
Effective: January 2026
Owner: Inventory &amp; Replenishment Team
Document version: 4.3

This procedure explains how store associates receive deliveries, restock the sales floor, count stock, and handle damaged or recalled goods at Contoso Retail.

---

## Receiving a delivery

1. Verify the delivery against the **Advance Shipping Notice (ASN)** in the back-office portal before signing for it.
2. Count the number of cartons or pallets and compare to the ASN. Note any shortage or overage on the carrier's paperwork **before** signing.
3. Inspect for visible damage. Photograph and refuse any clearly damaged outer cartons, recording the reason on the delivery note.
4. Scan each carton into the back-office system using **Receiving > Scan in**. The system marks the items as on-hand.
5. Move received stock to the stockroom staging area — never block fire exits or walkways with pallets.

## Putaway and replenishment

- Replenish the sales floor **front to back**: fill empty shelf facings first, then top up partially full ones.
- Practice **FIFO** (first in, first out): place newer stock behind existing stock so older units sell first. This is mandatory for dated and perishable goods.
- Confirm the **shelf label** matches the product and price. If a label is missing or wrong, print a new one at the price-check station before stocking the item.
- Break down and flatten empty cartons; move them to the baler or recycling area immediately to keep aisles clear.

## Triggering a restock order

Most replenishment is automatic, but managers can place manual orders:

1. Run **Inventory > Low stock report** to see items below their reorder point.
2. Review the suggested order quantities. Adjust for known local demand (events, weather, promotions).
3. Submit the order through **Inventory > Create replenishment order**. Orders submitted before the **2 PM cutoff** ship the same day.
4. Record any manual override reason so the demand-forecasting system can learn from it.

> **Note:** Do not manually order around a system "out of stock" without first checking for **phantom inventory** — stock the system thinks is on hand but is not (see Cycle counts below). Ordering on top of phantom inventory creates overstock.

## Cycle counts

- Count one **section per day** on a rotating schedule so the whole store is counted each month.
- High-value and high-shrink categories (electronics, fragrance) are counted **weekly**.
- Enter counts via **Inventory > Cycle count**. The system flags variances automatically.
- Investigate any variance over **10 units** or **$250** before accepting the count. Common causes: misplaced stock, unscanned receipts, theft, or mis-scans at the register.
- A manager must approve any count adjustment that writes off more than $250.

## Damaged, expired, and recalled stock

| Category | What to do |
|---|---|
| Damaged in store | Scan out via **Inventory > Damage-out**, record reason, move to the damage bin |
| Expired / past sell-by | Pull from the floor immediately, damage-out, dispose per local rules |
| Customer return (sellable) | Restock to the floor following FIFO |
| Customer return (not sellable) | Damage-out |
| Recalled item | Quarantine in the **recall bin**, never restock, follow the active recall notice |

## Stockroom organization

- Keep aisles and the receiving dock clear at all times.
- Store overstock in its labeled home location so it can be found for replenishment.
- Heavy items go on lower shelves; do not stack above the marked safe height.
- Report any damaged racking or unsafe stacking to the store manager before using that bay.

---

**Inventory &amp; Replenishment support:** replenishment@contoso.com or (555) 200-7766
**Recall hotline:** (555) 200-7799
