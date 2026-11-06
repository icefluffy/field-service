# Field Service - Client Order Quotations

Quotations (Odoo Sales) per client order and per dossier.

- **New quotation** on a client order: one quote for the whole request, with
  the client reference and a section per dossier (dossier - wagon). Add the
  products/prices under each section.
- **New quotation** on a dossier: a quote for that one wagon only (it is also
  linked to the client order).
- Smart buttons show the quotations; the client order shows the total of
  accepted (confirmed) quotations.
- Linked quotes are **not invoiced from Sales**: the work is invoiced from the
  client order or dossier based on completed FSM orders, so nothing is
  invoiced twice.

Depends on Sales (installed automatically). Install manually via Apps.
