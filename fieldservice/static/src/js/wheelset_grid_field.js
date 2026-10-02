/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WheelsetGridField extends Component {
    static template = "fieldservice.WheelsetGridField";
    static props = standardFieldProps;

    setup() {
        this.creating = new Map();
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

            return {
                position,
                record: byPosition.get(position) || null,
            };
        });
    }

    value(row, field) {
        if (row.record) {
            return row.record.data[field] ?? "";
        }

        return "";
    }

    async getOrCreateRecord(row) {
        if (row.record) {
            return row.record;
        }

        const relation = this.props.record.data[this.props.name];

        if (!this.creating.has(row.position)) {
            const promise = relation
                .addNewRecord({ position: "bottom" })
                .finally(() => {
                    this.creating.delete(row.position);
                });

            this.creating.set(row.position, promise);
        }

        const record = await this.creating.get(row.position);

        await record.update({
            position: row.position,
        });

        return record;
    }

    updateCell = async (row, field, value) => {
        const record = await this.getOrCreateRecord(row);

        await record.update({
            [field]: value,
        });
    };
}

registry.category("fields").add("wheelset_grid", {
    component: WheelsetGridField,
    supportedTypes: ["one2many"],
});