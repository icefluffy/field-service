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

    today() {
        const date = new Date();
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    }

    displayDate(value) {
        if (!value) {
            return "";
        }
        if (typeof value === "string") {
            const parts = value.split("-");
            if (parts.length === 3) {
                return `${parts[2]}-${parts[1]}-${parts[0]}`;
            }
            return value;
        }
        if (typeof value.toISODate === "function") {
            const iso = value.toISODate();
            const parts = iso.split("-");
            return `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
        if (typeof value.toFormat === "function") {
            return value.toFormat("dd-MM-yyyy");
        }
        return String(value);
    }

    parseDate(value) {
        const parts = value.trim().split("-");
        if (parts.length !== 3) {
            return null;
        }
        const [day, month, year] = parts;
        if (!/^\d{2}$/.test(day) || !/^\d{2}$/.test(month) || !/^\d{4}$/.test(year)) {
            return null;
        }
        const date = new Date(Number(year), Number(month) - 1, Number(day));
        if (
            date.getFullYear() !== Number(year) ||
            date.getMonth() !== Number(month) - 1 ||
            date.getDate() !== Number(day)
        ) {
            return null;
        }
        return `${year}-${month}-${day}`;
    }

    async getRecord(row) {
        if (row.record) return row.record;
        if (!this.pending.has(row.position)) {
            const relation = this.props.record.data[this.props.name];
            this.pending.set(row.position, (async () => {
                const record = await relation.addNewRecord({ position: "bottom" });
                await record.update({
                    position: row.position,
                    input_date: this.today(),
                });
                return record;
            })());
        }
        return this.pending.get(row.position);
    }

    updateCell = async (row, field, value) => {
        const record = await this.getRecord(row);
        await record.update({ [field]: value });
    };

    updateDate = async (row, value) => {
        const date = this.parseDate(value);
        if (!date) {
            return;
        }
        const record = await this.getRecord(row);
        await record.update({ input_date: date });
    };
}

registry.category("fields").add("wheelset_grid", {
    component: WheelsetGridField,
    supportedTypes: ["one2many"],
});
