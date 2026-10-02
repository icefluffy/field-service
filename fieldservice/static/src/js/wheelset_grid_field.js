/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WheelsetGridField extends Component {
    static template = "fieldservice.WheelsetGridField";
    static props = standardFieldProps;

    setup() {
        this.drafts = useState({});
    }

    get rows() {
        const relation = this.props.record.data[this.props.name];
        const records = relation?.records || [];
        const byPosition = new Map();
        for (const record of records) {
            if (record.data.position) byPosition.set(record.data.position, record);
        }
        return Array.from({ length: 8 }, (_, index) => {
            const position = index + 1;
            return { position, record: byPosition.get(position) || null };
        });
    }

    value(row, field) {
        if (row.record) return row.record.data[field] ?? "";
        return this.drafts[row.position]?.[field] ?? "";
    }

    async updateCell(row, field, value) {
        if (row.record) {
            await row.record.update({ [field]: value });
            return;
        }
        if (!this.drafts[row.position]) this.drafts[row.position] = {};
        this.drafts[row.position][field] = value;
        await this.props.record.update({
            [this.props.name]: [[0, 0, { position: row.position, ...this.drafts[row.position] }]],
        });
        delete this.drafts[row.position];
    }
}

registry.category("fields").add("wheelset_grid", {
    component: WheelsetGridField,
    supportedTypes: ["one2many"],
});
