/** @odoo-module **/
// Copyright 2026 TI-Consulting
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

/**
 * One2many that saves a new parent record before "Add a line", so the new
 * line (e.g. a dossier) is linked to the parent and gets its defaults
 * (client, reference, ...) immediately.
 */
export class One2ManySaveFirstField extends X2ManyField {
    async onAdd(params = {}) {
        const record = this.props.record;
        if (record.isNew) {
            const saved = await record.save();
            if (!saved) {
                return;
            }
            const inverse = record.fields[this.props.name].relation_field;
            const context = { ...(params.context || {}) };
            if (inverse) {
                context[`default_${inverse}`] = record.resId;
            }
            params = { ...params, context };
        }
        return super.onAdd(params);
    }
}

export const one2ManySaveFirstField = {
    ...x2ManyField,
    component: One2ManySaveFirstField,
};

registry.category("fields").add("one2many_save_first", one2ManySaveFirstField);
