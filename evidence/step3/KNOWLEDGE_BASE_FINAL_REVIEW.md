# Knowledge Base — Final Review (Part 1, Task 2)

**Fictional capstone policies:** These documents are original assignment content and are **not** representations of Nykaa commercial policies.

## Approved human edits (2026-10-14)

1. **KB-001:** Wrong-item returns explicitly allowed for all five categories within each category window.
2. **KB-007:** Seven-day points pending explained as initial return/cancellation adjustments, not full return-window coverage.
3. **KB-010:** Concealed damage after 48h clarified with reasonable evidence (photos or unboxing video).

## Cross-policy consistency

- KB-001 (15-day Apparel/Footwear returns) vs KB-009 (10-day size exchange): exchange remains stricter; consistent.
- KB-001 Beauty sealed returns vs KB-010 transit-documented broken-seal exception: compatible.
- KB-002 COD (7 business days) vs KB-006 prepaid cancel (5 business days): separate flows; unchanged.
- KB-007 no longer claims 7-day pending covers all category return windows.
- KB-012 unchanged; escalation INR thresholds remain fictional support rules.

## Validation

- `pytest tests/test_knowledge_base_drafts.py -v`: 5 passed
- `pytest tests/test_dataset.py -v`: 9 passed
- `pytest tests/test_step1b_smoke.py -v`: 6 passed
- `pip check`: No broken requirements found

See `evidence/step3/validation_all.txt`.

---


## KB-001 — Return Window by Product Category

**Topic:** return window by product category  
**Sentence count:** 5

### Policy body

This fictional demo storefront allows returns within category-specific windows counted from the delivery date. Apparel and Footwear may be returned within 15 days if items are unworn, unwashed, and include original tags and packaging. Beauty products may be returned within 7 days only when the seal is intact and the item is unused. Electronics and Home items may be returned within 10 days for manufacturing defects if the product is in resalable condition with all accessories. Wrong-item shipments may be returned in any category within that category's return window when the product is in resalable condition with tags, seals, and accessories as applicable.

---

## KB-002 — Cash on Delivery Refund Timelines

**Topic:** COD refund timelines  
**Sentence count:** 4

### Policy body

For cash-on-delivery orders, refunds are initiated only after the returned product passes quality inspection at our warehouse. Approved COD refunds are transferred to the bank account shared during the return request within 7 business days. If bank details are missing or invalid, the refund remains on hold until corrected details are verified by support. Customers receive SMS and email notifications when the refund is initiated and when it is marked completed.

---

## KB-003 — Standard Delivery Service Levels

**Topic:** delivery SLAs  
**Sentence count:** 4

### Policy body

Standard delivery for serviceable PIN codes in this demo catalog targets arrival within 4 to 7 business days after the order leaves our fulfillment center. Metro and tier-1 cities may receive express-eligible shipments within 2 to 3 business days when express shipping is selected at checkout. Delivery timelines exclude national holidays and severe weather delays declared by the courier partner. If an order exceeds the stated window by more than 2 business days, customers may contact support for a status trace.

---

## KB-004 — Reverse Pickup Eligibility

**Topic:** reverse-pickup eligibility  
**Sentence count:** 4

### Policy body

Reverse pickup is offered for eligible return requests when the order status is Delivered and the return is raised within the category return window defined in our return policy. Pickup is available only for serviceable PIN codes covered by our logistics partners. Items must be packed securely with the invoice copy placed inside the package. If reverse pickup is unavailable for a location, customers may ship the item using the prepaid label support provides after manual approval.

---

## KB-005 — Warranty Terms by Category

**Topic:** warranty terms by category  
**Sentence count:** 4

### Policy body

Electronics in this demo catalog include a 12-month limited warranty covering manufacturing defects under normal use; warranty claims require proof of purchase and a valid serial number where applicable. Beauty, Apparel, and Footwear items are sold without a long-term warranty and rely on the standard return window for quality issues discovered near delivery. Home products include a 6-month limited warranty against structural manufacturing defects but exclude normal wear, stains, or damage from misuse. Warranty service may involve repair, replacement, or store credit at our discretion after inspection.

---

## KB-006 — Order Cancellation Policy

**Topic:** order-cancellation policy  
**Sentence count:** 4

### Policy body

Orders in Placed status may be cancelled without charge within 60 minutes of order confirmation or before warehouse packing begins, whichever occurs first. Once an order moves to Shipped, cancellation is not available and the customer must use the return process after delivery if eligible. Partial cancellation of multi-item orders is allowed only while the order remains in Placed status. Refunds for cancelled prepaid orders are returned to the original payment method within 5 business days.

---

## KB-007 — Loyalty Points Redemption Policy

**Topic:** loyalty-points redemption policy  
**Sentence count:** 4

### Policy body

Demo Rewards points are credited after an order is marked Delivered and remain pending for 7 days to allow initial return or cancellation adjustments. A minimum balance of 200 points is required to redeem at checkout, and 1 point equals 1 INR of order value up to 20 percent of the cart subtotal. Points cannot be redeemed on cash-on-delivery orders or on gift-card-only purchases. Redeemed points are non-reversible once the order is confirmed.

---

## KB-008 — Payment Failure and Retry Policy

**Topic:** payment-failure/retry policy  
**Sentence count:** 4

### Policy body

If an online payment fails at checkout, the customer may retry up to three times within 30 minutes using the same or another saved payment method. An order is not confirmed until payment succeeds and an order confirmation is displayed. Repeated failures may trigger a temporary hold on checkout for fraud review, which support can clear after identity verification. Customers should not attempt duplicate orders while a payment retry is in progress.

---

## KB-009 — Size Exchange Policy

**Topic:** size-exchange policy  
**Sentence count:** 4

### Policy body

Size exchange is available only for Apparel and Footwear categories within 10 days of delivery when the requested alternate size is in stock. One free size exchange is permitted per order line item; the original item must be unworn with tags attached. Exchanges are processed as reverse pickup followed by forward shipment of the new size. If the desired size is unavailable, the customer may convert the request to a return for refund per the category return window.

---

## KB-010 — Damaged Item Claim Process

**Topic:** damaged-item claim process  
**Sentence count:** 4

### Policy body

Customers must report visible transit or packaging damage within 48 hours of delivery by opening a damage claim with the order ID and clear photos of the outer box and product. Concealed-damage claims reported after 48 hours may still be reviewed when supported by reasonable evidence, such as photos or an unboxing video. Approved claims receive replacement shipment or refund after inspection; customers may be asked to return the damaged unit via reverse pickup. Liquid or sealed Beauty items with broken seals are not eligible unless damage occurred during transit documented at delivery.

---

## KB-011 — International Shipping Restrictions

**Topic:** international shipping restrictions  
**Sentence count:** 4

### Policy body

This fictional demo storefront ships only to valid delivery addresses within India. International shipping, cross-border forwarding, and PO box addresses outside India are not supported. Orders with billing or shipping mismatches flagged as high risk may be cancelled before dispatch. Customers traveling abroad should ship to a domestic address or defer purchase until they return.

---

## KB-012 — Customer Support Escalation Matrix

**Topic:** customer-support escalation matrix  
**Sentence count:** 4

### Policy body

Level 1 support handles order tracking, policy explanations, and standard return initiation for order values under 5,000 INR. Level 2 supervisors review refund exceptions, repeated delivery failures, and cases involving order values from 5,000 INR up to 25,000 INR. Level 3 grievance specialists manage unresolved disputes, regulatory complaints, or any case open longer than 72 hours without resolution. Every escalation must include the order ID, prior ticket notes, and the customer’s preferred callback window.

---

**STATUS: TASK_2_FINALIZED**