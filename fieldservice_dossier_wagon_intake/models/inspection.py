from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError

ROWS = [('running', 'Wielstel', '21-'), ('running', 'T-stuk', '2162-'), ('running', 'Spiraalveer', '231-'), ('running', 'Bladveer', '232-'), ('running', 'Draaistel', '22-'), ('running', 'Glijstuk', '241-'), ('running', 'Aarding', '2491-'), ('running', 'Asplaat', '2323-'), ('frame', 'Vlamplaat', '3141-'), ('frame', 'Sleephaak', '3151-'), ('frame', 'Inscriptieplaat', '3221-'), ('frame', 'Brievenkast', '3222-'), ('body', 'Kast', '431-'), ('body', 'Deur (kast)', '432-'), ('body', 'Bak open bak', '441-'), ('body', 'Deur open bak', '442-'), ('body', 'Schuif open bak', '443-'), ('body', 'Schuifdak', '451-'), ('body', 'Huif', '452-'), ('body', 'Bediening schuifdak / huif', '453-'), ('body', 'Kanteldak', '461-'), ('body', 'Schuif kanteldak', '462-'), ('brake', 'Remblok', '5123-'), ('brake', '½-koppel', '5242-'), ('brake', 'Verdeler', '5211-'), ('brake', 'Remregelaar', '513-'), ('brake', 'Spuiklep (bediening)', '515-'), ('brake', 'Omschakeling', '515-'), ('brake', 'Eindkraan', '5251-'), ('brake', 'Weegklep', '522-'), ('coupling', 'Buffer', '611-'), ('coupling', 'Trekhaak', '6212-'), ('coupling', 'Schroefkoppeling', '6211-'), ('coupling', 'Glijplaat', '6213-'), ('maintenance', 'Preventief onderhoud / revisie / schildering / opschrift / beproeving', '')]
SECTIONS = [('running', 'Loopwerk (2)'), ('frame', 'Wagenraam (3)'),
            ('body', 'Bovenbouw (4)'), ('brake', 'Rem (5)'),
            ('coupling', 'Stoot- en trekwerk (6)'), ('maintenance', 'Onderhoud / revisie (9)')]

class Inspection(models.Model):
    _inherit = 'fsm.dossier.inspection'

    intake_report_ids = fields.One2many('fsm.wagon.intake', 'inspection_id', copy=False)
    is_wagon_intake = fields.Boolean(
        string="Is wagon intake",
        compute="_compute_is_wagon_intake",
    )

    @api.depends("type_id")
    def _compute_is_wagon_intake(self):
        intake_type = self.env.ref(
            "fieldservice_dossier.inspection_type_ik",
            raise_if_not_found=False,
        )
        for inspection in self:
            inspection.is_wagon_intake = bool(
                intake_type and inspection.type_id == intake_type
            )

    def action_open_wagon_intake(self):
        self.ensure_one()
        intake_type = self.env.ref('fieldservice_dossier.inspection_type_ik')
        if self.type_id != intake_type:
            raise UserError(_('This form is only for Ingangskeuring.'))
        report = self.intake_report_ids[:1]
        if not report:
            if self.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('This dossier is closed or cancelled.'))
            report = self.env['fsm.wagon.intake'].create({'inspection_id': self.id})
        return {'type': 'ir.actions.act_window', 'res_model': 'fsm.wagon.intake',
                'res_id': report.id, 'view_mode': 'form', 'target': 'current'}

class Order(models.Model):
    _inherit = 'fsm.order'

    def action_open_wagon_intake(self):
        self.ensure_one()
        intake_type = self.env.ref('fieldservice_dossier.inspection_type_ik')
        line = self.inspection_ids.filtered(lambda x: x.type_id == intake_type)
        if not line:
            raise UserError(_('First link the dossier Ingangskeuring line to this FSM order.'))
        return line.action_open_wagon_intake()

class Intake(models.Model):
    _name = 'fsm.wagon.intake'
    _description = 'Ingangsschouwing wagon'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True)
    inspection_id = fields.Many2one('fsm.dossier.inspection', required=True, ondelete='restrict', copy=False)
    dossier_id = fields.Many2one(related='inspection_id.dossier_id', store=True)
    equipment_id = fields.Many2one(related='inspection_id.equipment_id', store=True)
    order_id = fields.Many2one(related='inspection_id.order_id')
    company_id = fields.Many2one(related='inspection_id.company_id', store=True)
    state = fields.Selection([('draft','Niet gestart'), ('progress','In uitvoering'),
        ('passed','Geslaagd'), ('remarks','Geslaagd met opmerkingen'), ('failed','Afgekeurd')],
        default='draft', required=True, readonly=True, tracking=True, copy=False)
    inspection_date = fields.Date(default=fields.Date.context_today, required=True)
    inspector_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    recorded_by = fields.Many2one('res.users', readonly=True, copy=False)
    recorded_at = fields.Datetime(readonly=True, copy=False)
    holder_mark = fields.Char(string='Houdermerk')
    revision_mark = fields.Char(string='Revisiekader / REV')
    revision_date = fields.Date(string='Revisiedatum')
    brake_inscription = fields.Char(string='Remopschrift')
    uic = fields.Char(string='UIC')
    customer_type = fields.Char(string='Klanttype')
    tare_kg = fields.Float(string='Tarra (kg)')
    handbrake_t = fields.Float(string='Handrem (t)')
    handbrake_kn = fields.Float(string='Handrem (kN)')
    handbrake_percent = fields.Float(string='Handrem (%)')
    load_a = fields.Char(string='Lastenkader A')
    load_b = fields.Char(string='Lastenkader B')
    load_c = fields.Char(string='Lastenkader C')
    load_d = fields.Char(string='Lastenkader D')
    load_e = fields.Char(string='Lastenkader E')
    load_notes = fields.Text(string='Lastenkader - aanvullingen')
    extra = fields.Text(string='Extra')
    reason = fields.Text(string='Etiketgegevens / vermoedelijk motief')
    maintenance_inscriptions = fields.Text(string='Opschriften preventief onderhoud (PMB, F24, VSP, ...)')
    revision_plates = fields.Selection([('yes','Ja'),('no','Nee'),('na','Niet van toepassing')],
        string='Revisiewagon: VPI grondplaat / revisieplaatjes aanwezig?')
    brake_block_type = fields.Char(string='Rembloktype / maat',
        help='Papier: 320 / 250 mm; gietijzer / C810 / J816 / J816M / J838 / Abex / Cobra / LL. Controleer transcriptie.')
    remarks = fields.Text(string='Opmerkingen')
    outcome_note = fields.Text(string='Onderbouwing resultaat')
    line_ids = fields.One2many('fsm.wagon.intake.line', 'report_id', string='Vaststellingen', copy=False)
    source_reference = fields.Char(default='FG04-01_90-01.04 — Revisie 02 — 06/05/24', readonly=True)

    _sql_constraints = [('inspection_unique', 'unique(inspection_id)', 'Only one intake report per inspection.')]

    @api.depends('equipment_id', 'dossier_id')
    def _compute_name(self):
        for r in self:
            r.name = 'Ingangskeuring - %s - %s' % (r.equipment_id.display_name or '', r.dossier_id.display_name or '')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            line = self.env['fsm.dossier.inspection'].browse(vals.get('inspection_id'))
            if line.type_id != self.env.ref('fieldservice_dossier.inspection_type_ik'):
                raise ValidationError(_('An intake report requires an Ingangskeuring inspection.'))
            if line.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if vals.get('state', 'draft') != 'draft' or vals.get('recorded_by') or vals.get('recorded_at'):
                raise UserError(_('Use the result actions.'))
            vals['line_ids'] = [Command.create({'section': s, 'component': c, 'code': code, 'sequence': i * 10})
                                for i, (s, c, code) in enumerate(ROWS, 1)]
        return super().create(vals_list)

    def _check_editable(self):
        for r in self:
            if r.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if r.state not in ('draft', 'progress'):
                raise UserError(_('Reopen the report before changing it.'))

    def write(self, vals):
        if {'state', 'recorded_by', 'recorded_at', 'inspection_id'} & set(vals):
            raise UserError(_('Use the workflow buttons; the linked inspection cannot be changed.'))
        self._check_editable()
        return super().write(vals)

    def _workflow_write(self, vals):
        return super(Intake, self).write(vals)

    def action_start(self):
        self._check_editable()
        self._workflow_write({'state': 'progress'})
        for r in self:
            r.inspection_id.write({'work_status':'in_progress', 'result':'pending'})

    def _finish(self, result):
        self.ensure_one()
        self._check_editable()
        if self.state != 'progress':
            raise UserError(_('Start the inspection first.'))
        pending = self.line_ids.filtered(lambda l: l.check_state == 'pending')
        if pending:
            raise UserError(_('Assess every component (OK, defect or not applicable) first.'))
        if not self.line_ids or not self.inspector_id or not self.inspection_date:
            raise UserError(_('Inspector, date and inspection lines are required.'))
        if not self.outcome_note:
            raise UserError(_('Enter an explanation of the overall result.'))
        defects = self.line_ids.filtered(lambda l: l.check_state == 'defect')
        if result == 'passed' and defects:
            raise UserError(_('Unresolved recorded defects: choose Failed or Passed with remarks, as authorised by your procedure.'))
        self.inspection_id.write({'work_status':'done', 'result':result,
                                 'date_performed':self.inspection_date,
                                 'note':self.outcome_note})
        self._workflow_write({'state':result, 'recorded_by':self.env.user.id,
                              'recorded_at':fields.Datetime.now()})
        self.message_post(body=_('Result recorded: %s') % result)

    def action_pass(self):
        return self._finish('passed')
    def action_remarks(self):
        return self._finish('remarks')
    def action_fail(self):
        return self._finish('failed')

    def action_reopen(self):
        for r in self:
            if r.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if r.state in ('draft', 'progress'):
                raise UserError(_('This report is not final.'))
            r.inspection_id.write({'work_status':'in_progress','result':'pending'})
            r._workflow_write({'state':'progress', 'recorded_by':False, 'recorded_at':False})
            r.message_post(body=_('Report reopened; a new result must be recorded.'))

class IntakeLine(models.Model):
    _name = 'fsm.wagon.intake.line'
    _description = 'Ingangskeuring component'
    _order = 'sequence,id'
    report_id = fields.Many2one('fsm.wagon.intake', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='report_id.company_id', store=True)
    sequence = fields.Integer(default=500)
    section = fields.Selection(SECTIONS, required=True)
    component = fields.Char(string='Onderdeel', required=True)
    code = fields.Char(string='Groep / Cd')
    check_state = fields.Selection([('pending','Niet beoordeeld'),('ok','OK'),('defect','Defect'),('na','Niet van toepassing')], default='pending', required=True, string='Beoordeling')
    defect = fields.Text(string='Defect / vaststelling')
    quantity = fields.Integer(string='Aantal', default=0)
    note = fields.Char(string='Toelichting')

    @api.constrains('quantity','check_state','defect')
    def _check_defect(self):
        for l in self:
            if l.quantity < 0:
                raise ValidationError(_('Quantity cannot be negative.'))
            if l.check_state == 'defect' and (not l.defect or l.quantity < 1):
                raise ValidationError(_('For a defect, enter its description and a quantity of at least 1.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['fsm.wagon.intake'].browse(vals.get('report_id'))._check_editable()
        return super().create(vals_list)

    def write(self, vals):
        self.mapped('report_id')._check_editable()
        if 'report_id' in vals:
            raise UserError(_('You cannot move findings to another report.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(_('Keep the template rows; use Not applicable instead of deleting.'))
