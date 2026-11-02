Items delivered for a Field Service order are copied automatically to the order's Accounting tab
as **Contractor Costs** lines (marked *Material*, with their serial numbers).

* Trigger: validating a delivery (outgoing transfer) linked to the order, e.g. from the stock
  requests on the Inventory tab. One line per delivered stock move; syncing never duplicates.
* Returns are deducted from the line (and their serial numbers removed).
* Unit cost: the product cost, like a manually added contractor cost. The customer invoice prices
  the line with the client's pricelist and shows the serial numbers.
* From the Accounting tab the materials also go to the release form (Replaced components) and to
  the draft invoice. They are never put on a contractor's vendor bill.
* Invoiced orders are left untouched.
