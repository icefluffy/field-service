# Copyright Your Company
# License LGPL-3

from odoo import fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    # --- Top identification block ---
    # NOTE: 'name' (Order Reference / Auftragsnummer) and 'customer_id'
    # (Halter/ECM) already exist on fsm.order from the base fieldservice
    # module, so they are not redefined here.
    x_wagon_number = fields.Char(string="Wagennummer")
    x_fw_number = fields.Char(string="FW. Nummer", default="RSN")
    x_customer_order_ref = fields.Char(string="Kundenauftragsnummer")

    # --- Execution / maintenance level ---
    x_maintenance_level = fields.Char(string="Durchgeführte Instandhaltungsstufe")

    # --- Wagon technical data block ---
    x_wagon_number_old = fields.Char(string="Wagennummer Alt")
    x_own_weight = fields.Float(string="Eigengewicht (kg)")
    x_revision_cycle = fields.Char(string="Zyklus (Revision)")
    x_revision_date = fields.Date(string="Datum (Revision)")
    x_revision_extension = fields.Char(string="Verlängerung (Revision)")
    x_brake_type = fields.Char(string="Bremsrevision")
    x_brake_deadline = fields.Date(string="Frist (Bremsrevision)")

    # --- Free-text blocks ---
    x_work_performed = fields.Html(string="Durchgeführte Instandsetzungsarbeiten")
    x_postponed_work = fields.Html(string="Zurückgestellte Arbeiten (einschließlich Begründung)")
    x_replaced_components = fields.Html(string="Ausgetauschte Komponenten")
    x_other_information = fields.Html(string="Sonstige Angaben (nach Vorgabe des Halters/ECM)")

    # --- Release confirmation ---
    x_repair_confirmed = fields.Boolean(string="Instandsetzung bestätigt")
    x_release_confirmed = fields.Boolean(string="Betriebsfreigabe bestätigt")

    # --- Signatory block ---
    # 'person_id' (assigned FSM worker) already exists on fsm.order; used
    # in the report for the responsible employee's name.
    x_issue_date = fields.Date(string="Ausstellungsdatum")
