# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Group existing dossiers that share a client and reference.

    Every (company, client, reference) found on existing, not-cancelled
    dossiers becomes one client order, and those dossiers are linked to it.
    Dossiers without a reference or without a client stay as they are.
    """
    dossiers = env["fsm.dossier"].search([
        ("customer_reference", "!=", False),
        ("customer_id", "!=", False),
        ("state", "!=", "cancelled"),
        ("client_order_id", "=", False),
    ], order="id")
    groups = {}
    for dossier in dossiers:
        reference = dossier.customer_reference.strip()
        if not reference:
            continue
        key = (
            dossier.company_id.id,
            dossier.customer_id.commercial_partner_id.id,
            reference.lower(),
        )
        groups.setdefault(key, (reference, env["fsm.dossier"]))
        groups[key] = (groups[key][0], groups[key][1] | dossier)
    for (company_id, partner_id, _key), (reference, members) in groups.items():
        first = members.sorted("id")[:1]
        order = env["fsm.client.order"].with_company(company_id).create({
            "reference": reference,
            "customer_id": partner_id,
            "company_id": company_id,
            "team_id": first.team_id.id,
            "user_id": first.user_id.id,
            "date_received": first.create_date.date(),
            "state": (
                "closed" if all(d.state == "closed" for d in members) else "open"
            ),
        })
        members.with_context(client_order_sync=True).write(
            {"client_order_id": order.id}
        )
    _logger.info("Client orders created for existing dossiers: %s", len(groups))
