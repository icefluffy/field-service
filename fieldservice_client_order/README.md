# Field Service - Client Orders

Groups the dossiers (one per wagon) of one client request - an order, an
e-mail, a phone call - under a **Client Order** with one client reference.

## What it does

- Menu **Dossiers > Client Orders**: number (CO/00001), client, client
  reference, contact, received/planned dates, team, coordinator and the
  client's request (paste the e-mail; attach the original in the chatter).
- **Add wagons**: pick several wagons, one dossier is created per wagon with
  the client and reference of the client order.
- The client reference is kept in sync: changing it on the client order
  changes it on all dossiers and their (not closed) FSM orders. On a linked
  dossier the reference is read-only.
- Safeguards: one client per client order (dossiers must have the same
  client), a reference can be used only once per client.
- **Create invoice**: one combined draft invoice for the completed FSM orders
  of all dossiers, with a section per dossier (dossier - wagon), the client
  reference as invoice reference and the client order as origin. Orders that
  are not completed, already invoiced or without billable lines are shown but
  not selectable. Per-dossier invoicing keeps working as before.

## Installation

Install manually via Apps (Update Apps List first). On installation, existing
dossiers that share the same client and reference are grouped into client
orders automatically (case and spaces ignored).

Quotations: install **Field Service - Client Order Quotations**.
