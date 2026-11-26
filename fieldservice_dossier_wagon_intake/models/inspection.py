# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


# Component names are translatable (see i18n/*.po); the English text is the
# source and every active language gets its translation when a report is made.
ROWS = [
    ('running', _lt('Wheelset'), '21-'),
    ('running', _lt('T-piece'), '2162-'),
    ('running', _lt('Coil spring'), '231-'),
    ('running', _lt('Leaf spring'), '232-'),
    ('running', _lt('Bogie'), '22-'),
    ('running', _lt('Sliding piece'), '241-'),
    ('running', _lt('Earthing'), '2491-'),
    ('running', _lt('Axle plate'), '2323-'),
    ('frame', _lt('Flame plate'), '3141-'),
    ('frame', _lt('Towing hook'), '3151-'),
    ('frame', _lt('Inscription plate'), '3221-'),
    ('frame', _lt('Letter box'), '3222-'),
    ('body', _lt('Box'), '431-'),
    ('body', _lt('Door (box)'), '432-'),
    ('body', _lt('Open wagon body'), '441-'),
    ('body', _lt('Open wagon door'), '442-'),
    ('body', _lt('Open wagon slide'), '443-'),
    ('body', _lt('Sliding roof'), '451-'),
    ('body', _lt('Hood'), '452-'),
    ('body', _lt('Sliding roof / hood operation'), '453-'),
    ('body', _lt('Tilting roof'), '461-'),
    ('body', _lt('Sliding tilting roof'), '462-'),
    ('brake', _lt('Brake block'), '5123-'),
    ('brake', _lt('½ coupling'), '5242-'),
    ('brake', _lt('Distributor'), '5211-'),
    ('brake', _lt('Brake regulator'), '513-'),
    ('brake', _lt('Release valve (operation)'), '515-'),
    ('brake', _lt('Changeover'), '515-'),
    ('brake', _lt('End cock'), '5251-'),
    ('brake', _lt('Load-weighing valve'), '522-'),
    ('coupling', _lt('Buffer'), '611-'),
    ('coupling', _lt('Draw hook'), '6212-'),
    ('coupling', _lt('Screw coupling'), '6211-'),
    ('coupling', _lt('Sliding plate'), '6213-'),
    ('maintenance', _lt('Preventive maintenance / overhaul / painting / inscription / testing'), ''),
]
# Component names of reports made before the form was translated to English.
LEGACY_DUTCH_COMPONENTS = {
    'Wielstel': 'Wheelset',
    'T-stuk': 'T-piece',
    'Spiraalveer': 'Coil spring',
    'Bladveer': 'Leaf spring',
    'Draaistel': 'Bogie',
    'Glijstuk': 'Sliding piece',
    'Aarding': 'Earthing',
    'Asplaat': 'Axle plate',
    'Vlamplaat': 'Flame plate',
    'Sleephaak': 'Towing hook',
    'Inscriptieplaat': 'Inscription plate',
    'Brievenkast': 'Letter box',
    'Kast': 'Box',
    'Deur (kast)': 'Door (box)',
    'Bak open bak': 'Open wagon body',
    'Deur open bak': 'Open wagon door',
    'Schuif open bak': 'Open wagon slide',
    'Schuifdak': 'Sliding roof',
    'Huif': 'Hood',
    'Bediening schuifdak / huif': 'Sliding roof / hood operation',
    'Kanteldak': 'Tilting roof',
    'Schuif kanteldak': 'Sliding tilting roof',
    'Remblok': 'Brake block',
    '½-koppel': '½ coupling',
    'Verdeler': 'Distributor',
    'Remregelaar': 'Brake regulator',
    'Spuiklep (bediening)': 'Release valve (operation)',
    'Omschakeling': 'Changeover',
    'Eindkraan': 'End cock',
    'Weegklep': 'Load-weighing valve',
    'Trekhaak': 'Draw hook',
    'Schroefkoppeling': 'Screw coupling',
    'Glijplaat': 'Sliding plate',
    'Preventief onderhoud / revisie / schildering / opschrift / beproeving': 'Preventive maintenance / overhaul / painting / inscription / testing',
}
SECTIONS = [('running', 'Running gear (2)'), ('frame', 'Wagon frame (3)'),
            ('body', 'Superstructure (4)'), ('brake', 'Brake (5)'),
            ('coupling', 'Buffing and draw gear (6)'), ('maintenance', 'Maintenance / overhaul (9)')]


# Intake field -> label (case-insensitive) of the wagon's lot property.
WAGON_PROPERTY_LABELS = {
    'revision_mark': 'revision frame',
    'uic': 'uic code',
    'tare_kg': 'tare',
}

# Fields the inspector must fill in before the inspection can be completed.
# Editing any of them (or a finding) moves a new report to In progress.
# Numeric fields count as empty while they are 0.
COMPLETION_FIELDS = [
    'inspection_date', 'inspector_id', 'keeper_id', 'revision_mark',
    'revision_date', 'brake_inscription', 'uic', 'customer_type', 'tare_kg',
    'handbrake_t', 'handbrake_kn', 'handbrake_percent',
    'load_a', 'load_b', 'load_c', 'load_d', 'load_e', 'load_notes',
    'extra', 'reason', 'maintenance_inscriptions', 'revision_plates',
    'brake_block_type', 'remarks', 'outcome_note',
]
INPUT_FIELDS = set(COMPLETION_FIELDS) | {'line_ids', 'holder_mark'}
LINE_INPUT_FIELDS = {'check_state', 'defect', 'quantity', 'note'}
OPEN_STATES = ('draft', 'progress')


def _convert_property_value(value, target_type):
    """Convert a value between a property type and an intake field type."""
    if value in (None, False, ''):
        return None
    if target_type in ('float', 'integer'):
        if isinstance(value, str):
            try:
                value = float(value.strip().replace(' ', '').replace(',', '.'))
            except ValueError:
                return None
        return int(value) if target_type == 'integer' else float(value)
    if target_type == 'char':
        if isinstance(value, float):
            return ('%f' % value).rstrip('0').rstrip('.')
        return str(value)
    return None


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
            raise UserError(_('This form is only for Inbound inspection.'))
        if not self.order_id:
            raise UserError(_(
                "First link a work order to the %s line (use the + button).",
                self.type_id.name,
            ))
        report = self.intake_report_ids[:1]
        if not report:
            if self.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('This dossier is closed or cancelled.'))
            report = self.env['fsm.wagon.intake'].create({'inspection_id': self.id})
        return {'type': 'ir.actions.act_window', 'res_model': 'fsm.wagon.intake',
                'res_id': report.id, 'view_mode': 'form', 'target': 'current'}


class Order(models.Model):
    _inherit = 'fsm.order'

    has_wagon_intake = fields.Boolean(
        string="Has inbound inspection",
        compute="_compute_has_wagon_intake",
        help="True when the dossier Inbound inspection line is linked to this work order.",
    )

    @api.depends("inspection_ids.type_id")
    def _compute_has_wagon_intake(self):
        intake_type = self.env.ref(
            "fieldservice_dossier.inspection_type_ik", raise_if_not_found=False,
        )
        for order in self:
            order.has_wagon_intake = bool(intake_type) and any(
                line.type_id == intake_type for line in order.inspection_ids
            )

    def action_open_wagon_intake(self):
        self.ensure_one()
        intake_type = self.env.ref('fieldservice_dossier.inspection_type_ik')
        line = self.inspection_ids.filtered(lambda x: x.type_id == intake_type)
        if not line:
            raise UserError(_('First link the dossier Inbound inspection line to this FSM order.'))
        return line.action_open_wagon_intake()


class Intake(models.Model):
    _name = 'fsm.wagon.intake'
    _description = 'Inbound wagon inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'


    # Not stored: the title follows the language of whoever views the report.
    name = fields.Char(compute='_compute_name', search='_search_name')
    inspection_id = fields.Many2one('fsm.dossier.inspection', required=True, ondelete='restrict', copy=False)
    dossier_id = fields.Many2one(related='inspection_id.dossier_id', store=True)
    equipment_id = fields.Many2one(related='inspection_id.equipment_id', store=True)
    order_id = fields.Many2one(related='inspection_id.order_id')
    company_id = fields.Many2one(related='inspection_id.company_id', store=True)
    state = fields.Selection([('draft', 'Not started'), ('progress', 'In progress'),
        ('done', 'Completed')],
        default='draft', required=True, readonly=True, tracking=True, copy=False)
    inspection_date = fields.Date(default=fields.Date.context_today, required=True)
    inspector_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    recorded_by = fields.Many2one('res.users', readonly=True, copy=False)
    recorded_at = fields.Datetime(readonly=True, copy=False)
    holder_mark = fields.Char(string='Keeper (old text)')
    keeper_id = fields.Many2one(
        'res.partner', string='Keeper', compute='_compute_wagon_data',
        inverse='_inverse_keeper_id', store=True, readonly=False,
        help="Synchronised with the wagon's Managed By field.")
    revision_mark = fields.Char(
        string='Revision frame / REV', compute='_compute_wagon_data',
        inverse='_inverse_wagon_properties', store=True, readonly=False,
        help="Synchronised with the wagon's Revision frame property.")
    revision_date = fields.Date(string='Revision date')
    brake_inscription = fields.Char(string='Brake inscription')
    uic = fields.Char(
        string='UIC', compute='_compute_wagon_data',
        inverse='_inverse_wagon_properties', store=True, readonly=False,
        help="Synchronised with the wagon's UIC code property.")
    customer_type = fields.Char(string='Customer type')
    tare_kg = fields.Float(
        string='Tare (kg)', compute='_compute_wagon_data',
        inverse='_inverse_wagon_properties', store=True, readonly=False,
        help="Synchronised with the wagon's Tare property.")
    handbrake_t = fields.Float(string='Handbrake (t)')
    handbrake_kn = fields.Float(string='Handbrake (kN)')
    handbrake_percent = fields.Float(string='Handbrake (%)')
    load_a = fields.Char(string='Load limit raster  A')
    load_b = fields.Char(string='Load limit raster  B')
    load_c = fields.Char(string='Load limit raster  C')
    load_d = fields.Char(string='Load limit raster  D')
    load_e = fields.Char(string='Load limit raster  E')
    load_notes = fields.Text(string='Load limit raster  - additions / remarks')
    extra = fields.Text(string='Extra')
    reason = fields.Text(string='Label information / probable cause')
    maintenance_inscriptions = fields.Text(string='Preventive maintenance signage (PMB, F24, VSP, ...)')
    revision_plates = fields.Selection([('yes','Yes'),('no','No'),('na','Not applicable')],
        string='Overhaul wagon: VPI base plate / overhaul plates present?')
    brake_block_type = fields.Char(string='Brake block type / size',
        help='Paper: 320 / 250 mm; cast iron / C810 / J816 / J816M / J838 / Abex / Cobra / LL. Check transcription.')
    remarks = fields.Text(string='Remarks')
    outcome_note = fields.Text(string='Conclusion')
    line_ids = fields.One2many('fsm.wagon.intake.line', 'report_id', string='Findings', copy=False)
    source_reference = fields.Char(default='FG04-01_90-01.04 — Revision 02 — 06/05/24', readonly=True)


    _sql_constraints = [('inspection_unique', 'unique(inspection_id)', 'Only one intake report per inspection.')]


    def _wagon_property_definitions(self):
        """Map intake fields to the wagon's lot property definitions (by label)."""
        self.ensure_one()
        definition = self.equipment_id.product_id.lot_properties_definition or []
        by_label = {
            (prop.get('string') or '').strip().casefold(): prop
            for prop in definition
            if isinstance(prop, dict) and prop.get('name')
        }
        return {
            fname: by_label[label]
            for fname, label in WAGON_PROPERTY_LABELS.items()
            if label in by_label
        }


    @api.depends('equipment_id.managed_by_id', 'equipment_id.lot_properties')
    def _compute_wagon_data(self):
        # The wagon is the source of truth while the report is open; a value
        # already on the report is kept when the wagon has none. Recorded
        # (final) reports keep the values they were recorded with.
        for r in self:
            if r.state not in ('draft', 'progress'):
                r.keeper_id = r.keeper_id
                r.revision_mark = r.revision_mark
                r.uic = r.uic
                r.tare_kg = r.tare_kg
                continue
            r.keeper_id = r.equipment_id.managed_by_id or r.keeper_id
            values = r.equipment_id.lot_properties or {}
            definitions = r._wagon_property_definitions() if r.equipment_id else {}
            for fname in WAGON_PROPERTY_LABELS:
                prop = definitions.get(fname)
                value = values.get(prop['name']) if prop else None
                value = _convert_property_value(value, r._fields[fname].type)
                r[fname] = value if value not in (None, False, '', 0, 0.0) else r[fname]


    def _inverse_keeper_id(self):
        for r in self:
            if r.equipment_id and r.keeper_id and r.equipment_id.managed_by_id != r.keeper_id:
                r.equipment_id.managed_by_id = r.keeper_id


    def _inverse_wagon_properties(self):
        for r in self:
            equipment = r.equipment_id
            if not equipment.lot_id:
                continue
            values = dict(equipment.lot_properties or {})
            changed = False
            for fname, prop in r._wagon_property_definitions().items():
                if not r[fname]:
                    continue
                new_value = _convert_property_value(r[fname], prop.get('type'))
                if new_value is None or values.get(prop['name']) == new_value:
                    continue
                values[prop['name']] = new_value
                changed = True
            if changed:
                # Inspectors may not have stock rights; only these keys change.
                equipment.lot_id.sudo().lot_properties = values


    def _get_missing_info(self):
        """Return the labels of the fields and findings that are still empty."""
        self.ensure_one()
        missing = [
            self._fields[fname]._description_string(self.env)
            for fname in COMPLETION_FIELDS
            if not self[fname]
        ]
        pending = self.line_ids.filtered(lambda l: l.check_state == 'pending')
        if not self.line_ids:
            missing.append(_('Findings'))
        elif pending:
            missing.append(_('Findings: %(count)s component(s) not assessed (%(names)s)') % {
                'count': len(pending),
                'names': ', '.join(pending.mapped('component')),
            })
        return missing


    @api.depends('equipment_id', 'dossier_id')
    @api.depends_context('lang')
    def _compute_name(self):
        label = self.env._('Inbound inspection')
        for r in self:
            r.name = '%s - %s - %s' % (
                label, r.equipment_id.display_name or '', r.dossier_id.display_name or '')

    @api.depends('name')
    @api.depends_context('lang')
    def _compute_display_name(self):
        for r in self:
            r.display_name = r.name

    def _search_name(self, operator, value):
        # The title is built from the wagon and the dossier, so search on those.
        if not isinstance(value, str):
            return [('id', '=', 0)] if operator not in expression.NEGATIVE_TERM_OPERATORS else []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return ['&', ('equipment_id', operator, value), ('dossier_id', operator, value)]
        return ['|', ('equipment_id', operator, value), ('dossier_id', operator, value)]


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            line = self.env['fsm.dossier.inspection'].browse(vals.get('inspection_id'))
            if line.type_id != self.env.ref('fieldservice_dossier.inspection_type_ik'):
                raise ValidationError(_('An intake report requires an Inbound inspection.'))
            if line.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if vals.get('state', 'draft') != 'draft' or vals.get('recorded_by') or vals.get('recorded_at'):
                raise UserError(_('Use the workflow buttons.'))
            vals['line_ids'] = [Command.create({'section': s, 'component': c._source, 'code': code, 'sequence': i * 10})
                                for i, (s, c, code) in enumerate(ROWS, 1)]
        reports = super().create(vals_list)
        reports.line_ids._set_component_translations()
        return reports


    def _check_editable(self):
        for r in self:
            if r.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if r.state not in OPEN_STATES:
                raise UserError(_('Reopen the report before changing it.'))


    def write(self, vals):
        if {'state', 'recorded_by', 'recorded_at', 'inspection_id'} & set(vals):
            raise UserError(_('Use the workflow buttons; the linked inspection cannot be changed.'))
        self._check_editable()
        if INPUT_FIELDS & set(vals):
            self._mark_in_progress()
        return super().write(vals)


    def _mark_in_progress(self):
        """Move reports that are not started yet to In progress."""
        todo = self.filtered(lambda r: r.state == 'draft')
        if todo:
            todo._workflow_write({'state': 'progress'})
            todo.inspection_id.write({'work_status': 'in_progress', 'result': 'pending'})


    def _workflow_write(self, vals):
        return super(Intake, self).write(vals)


    def action_start(self):
        self._check_editable()
        self._mark_in_progress()


    def action_complete(self):
        """Complete the inspection once every field and finding is filled in.

        An inbound wagon is always damaged, so there is no pass/fail outcome:
        the dossier line is marked done with result Not applicable, which the
        dossier approval accepts.
        """
        for r in self:
            r._check_editable()
            missing = r._get_missing_info()
            if missing:
                raise UserError(
                    _('Fill in all fields before completing the inspection. Still missing:\n%s')
                    % '\n'.join('- %s' % m for m in missing))
            r.inspection_id.write({'work_status': 'done', 'result': 'na',
                                   'date_performed': r.inspection_date,
                                   'note': r.outcome_note})
            r._workflow_write({'state': 'done', 'recorded_by': self.env.user.id,
                               'recorded_at': fields.Datetime.now()})
            r.message_post(body=_('Inbound inspection completed.'))


    def action_reopen(self):
        for r in self:
            if r.dossier_id.state in ('closed', 'cancelled'):
                raise UserError(_('Dossier is closed or cancelled.'))
            if r.state in OPEN_STATES:
                raise UserError(_('This report is not completed.'))
            r.inspection_id.write({'work_status':'in_progress','result':'pending'})
            r._workflow_write({'state':'progress', 'recorded_by':False, 'recorded_at':False})
            r.message_post(body=_('Report reopened; complete it again when finished.'))


class IntakeLine(models.Model):
    _name = 'fsm.wagon.intake.line'
    _description = 'Inbound inspection component'
    _order = 'sequence,id'
    report_id = fields.Many2one('fsm.wagon.intake', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='report_id.company_id', store=True)
    sequence = fields.Integer(default=500)
    section = fields.Selection(SECTIONS, required=True)
    component = fields.Char(string='Component', required=True, translate=True)
    code = fields.Char(string='Group / Code')
    check_state = fields.Selection([('pending','Not assessed'),('ok','OK'),('defect','Defect'),('na','Not applicable')], default='pending', required=True, string='Assessment')
    defect = fields.Text(string='Defect / finding')
    quantity = fields.Integer(string='Quantity', default=0)
    note = fields.Char(string='Explanation')


    def _set_component_translations(self):
        """Fill every active language with the translation of the template row.

        Lines are matched on their English text (or the original Dutch text of
        reports made before the form was translated); lines whose component was
        typed in by hand are left alone.
        """
        langs = [code for code, _name in self.env['res.lang'].get_installed()]
        by_source = {}
        for _section, label, _code in ROWS:
            values = {lang: label._translate(lang) for lang in langs}
            values['en_US'] = label._source
            by_source[label._source] = values
        by_source.update({nl: by_source[en] for nl, en in LEGACY_DUTCH_COMPONENTS.items()})
        for line in self.sudo():
            stored = line.with_context(lang='en_US').component
            values = by_source.get(stored)
            if values:
                line.update_field_translations('component', dict(values))

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
        reports = self.mapped('report_id')
        reports._check_editable()
        if 'report_id' in vals:
            raise UserError(_('You cannot move findings to another report.'))
        if LINE_INPUT_FIELDS & set(vals):
            reports._mark_in_progress()
        return super().write(vals)


    def unlink(self):
        raise UserError(_('Keep the template rows; use Not applicable instead of deleting.'))