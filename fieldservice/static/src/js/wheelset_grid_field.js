/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WheelsetGridField extends Component {
    static template = "fieldservice.WheelsetGridField";
    static props = standardFieldProps;

    setup() {
        this.pending = new Map();
    }

    get rows() {
        const relation = this.props.record.data[this.props.name];
        const records = relation?.records || [];
        const byPosition = new Map();
        for (const record of records) {
            if (record.data.position) {
                byPosition.set(record.data.position, record);
            }
        }
        return Array.from({ length: 8 }, (_, index) => {
            const position = index + 1;
            return { position, record: byPosition.get(position) || null };
        });
    }

    value(row, field) {
        return row.record?.data[field] ?? "";
    }

    async getRecord(row) {
        if (row.record) return row.record;
        if (!this.pending.has(row.position)) {
            const relation = this.props.record.data[this.props.name];
            this.pending.set(row.position, (async () => {
                const record = await relation.addNewRecord({ position: "bottom" });
                await record.update({ position: row.position });
                return record;
            })());
        }
        return this.pending.get(row.position);
    }

    updateCell = async (row, field, value) => {
        const record = await this.getRecord(row);
        await record.update({ [field]: value });
    };
}

registry.category("fields").add("wheelset_grid", {
    component: WheelsetGridField,
    supportedTypes: ["one2many"],
});
