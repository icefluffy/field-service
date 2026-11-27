/** @odoo-module **/
// Copyright 2026 TI-Consulting
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
//
// Load limit raster (lastgrensraster) of the Inbound inspection, drawn like
// the plate on the wagon: line categories as columns, one row per speed and
// merged cells where the plate has one value for several categories.
// The data shape is described in models/load_grid.py.
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/core/utils/numbers";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// Older plates: A, B, C, D (E). Newer plates: EN 15528 line categories.
const CLASSIC = ["A", "B", "C", "D", "E"];
const EN = ["A", "B1", "B2", "C2", "C3", "C4", "D2", "D3", "D4", "E4", "E5"];
const CLASSIC_ONLY = CLASSIC.filter((c) => !EN.includes(c));
const EN_ONLY = EN.filter((c) => !CLASSIC.includes(c));
const SPEED_ORDER = { "": 80, 90: 90, S: 100, SS: 120 };
const PRESET_SPEEDS = ["", "90", "S", "SS"];

function emptyGrid() {
    return { columns: [], header_joins: [], rows: [] };
}

/** Copy of the stored grid with every list as long as it should be. */
function cleanGrid(raw) {
    const grid = raw && typeof raw === "object" ? raw : emptyGrid();
    const columns = Array.isArray(grid.columns) ? [...grid.columns] : [];
    const n = columns.length;
    const fixJoins = (joins) =>
        Array.from({ length: Math.max(n - 1, 0) }, (_, i) => Boolean((joins || [])[i]));
    return {
        columns,
        header_joins: fixJoins(grid.header_joins),
        rows: (Array.isArray(grid.rows) ? grid.rows : []).map((row) => ({
            speed: row.speed || "",
            values: Array.from({ length: n }, (_, i) => {
                const v = (row.values || [])[i];
                return typeof v === "number" ? v : null;
            }),
            joins: fixJoins(row.joins),
        })),
    };
}

/** [start, end) of each cell of a row; end excluded. */
function segments(joins, length) {
    const result = [];
    let start = 0;
    for (let i = 0; i < length; i++) {
        if (i === length - 1 || !joins[i]) {
            result.push({ start, end: i + 1 });
            start = i + 1;
        }
    }
    return result;
}

function speedKmh(speed) {
    if (speed in SPEED_ORDER) {
        return SPEED_ORDER[speed];
    }
    const kmh = parseInt(speed, 10);
    return Number.isFinite(kmh) ? kmh : 999;
}

export class LoadGridField extends Component {
    static template = "fieldservice_dossier_wagon_intake.LoadGridField";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ mergeMode: false });
        // Changes run one after the other, each on the result of the last
        // one, so quick taps on a phone never overwrite each other.
        this.queue = Promise.resolve();
        this.classicCategories = CLASSIC;
        this.enCategories = EN_ONLY;
    }

    get grid() {
        return cleanGrid(this.props.record.data[this.props.name]);
    }

    get isEmpty() {
        const grid = this.grid;
        return !grid.columns.length && !grid.rows.length;
    }

    get headerCells() {
        const grid = this.grid;
        return segments(grid.header_joins, grid.columns.length).map((seg) => ({
            ...seg,
            label: grid.columns.slice(seg.start, seg.end).join(" "),
            span: seg.end - seg.start,
        }));
    }

    get rows() {
        const grid = this.grid;
        return grid.rows.map((row, index) => ({
            index,
            speed: row.speed,
            isPreset: PRESET_SPEEDS.includes(row.speed),
            cells: segments(row.joins, grid.columns.length).map((seg) => ({
                ...seg,
                span: seg.end - seg.start,
                value: row.values[seg.start],
            })),
        }));
    }

    get speedChoices() {
        return [
            { value: "", label: _t("– (80 km/h)") },
            { value: "90", label: _t("90 (90 km/h)") },
            { value: "S", label: _t("S (100 km/h)") },
            { value: "SS", label: _t("SS (120 km/h)") },
            { value: "other", label: _t("Other speed (km/h)") },
        ];
    }

    isSelected(category) {
        return this.grid.columns.includes(category);
    }

    formatValue(value) {
        if (value === null || value === undefined) {
            return "";
        }
        return formatFloat(value, { digits: [16, 1] });
    }

    displayValue(value) {
        return value === null || value === undefined ? "" : `${this.formatValue(value)} t`;
    }

    speedLabel(speed) {
        return speed;
    }

    /** Apply ``change(grid)`` to the current grid and store the result. */
    mutate(change) {
        const done = this.queue.then(async () => {
            const grid = change(this.grid);
            if (grid) {
                await this.props.record.update({ [this.props.name]: grid });
            }
        });
        // A failed change must not block the next ones.
        this.queue = done.catch(() => {});
        return done;
    }

    // Line categories ------------------------------------------------------

    toggleCategory(category) {
        return this.mutate((grid) => {
            let wanted = new Set(grid.columns);
            if (wanted.has(category)) {
                wanted.delete(category);
            } else {
                wanted.add(category);
                // A plate uses either the old letters or the EN 15528 categories.
                const other = CLASSIC_ONLY.includes(category) ? EN_ONLY : CLASSIC_ONLY;
                wanted = new Set([...wanted].filter((c) => !other.includes(c)));
            }
            const order = [...wanted].some((c) => CLASSIC_ONLY.includes(c)) ? CLASSIC : EN;
            const columns = order.filter((c) => wanted.has(c));
            const oldIndex = Object.fromEntries(grid.columns.map((c, i) => [c, i]));
            const remapJoins = (joins) =>
                columns.slice(0, -1).map((c, i) => {
                    const a = oldIndex[c];
                    const b = oldIndex[columns[i + 1]];
                    return a !== undefined && b === a + 1 && Boolean(joins[a]);
                });
            const rows = grid.rows.map((row) => ({
                speed: row.speed,
                values: columns.map((c) => (c in oldIndex ? row.values[oldIndex[c]] : null)),
                joins: remapJoins(row.joins),
            }));
            if (columns.length && !rows.length) {
                rows.push({ speed: "", values: columns.map(() => null), joins: remapJoins([]) });
            }
            return { columns, header_joins: remapJoins(grid.header_joins), rows };
        });
    }

    // Rows -----------------------------------------------------------------

    nextSpeed(grid) {
        const used = new Set(grid.rows.map((r) => r.speed));
        return ["", "S", "SS", "90"].find((s) => !used.has(s)) ?? "120";
    }

    addRow() {
        return this.mutate((grid) => {
            const n = grid.columns.length;
            grid.rows.push({
                speed: this.nextSpeed(grid),
                values: Array(n).fill(null),
                joins: Array(Math.max(n - 1, 0)).fill(false),
            });
            return this.sortRows(grid);
        });
    }

    /** "120 | 00,0 t": the wagon may only run at 120 km/h when empty. */
    addEmptyOnlyRow() {
        return this.mutate((grid) => {
            const n = grid.columns.length;
            grid.rows = grid.rows.filter((r) => r.speed !== "120");
            grid.rows.push({
                speed: "120",
                values: Array(n).fill(0),
                joins: Array(Math.max(n - 1, 0)).fill(true),
            });
            return this.sortRows(grid);
        });
    }

    removeRow(index) {
        return this.mutate((grid) => {
            grid.rows.splice(index, 1);
            return grid;
        });
    }

    sortRows(grid) {
        grid.rows.sort((a, b) => speedKmh(a.speed) - speedKmh(b.speed));
        return grid;
    }

    onSpeedSelect(index, ev) {
        const value = ev.target.value;
        return this.mutate((grid) => {
            grid.rows[index].speed = value === "other" ? "120" : value;
            return this.sortRows(grid);
        });
    }

    onSpeedNumber(index, ev) {
        const kmh = parseInt(ev.target.value, 10);
        return this.mutate((grid) => {
            grid.rows[index].speed = Number.isFinite(kmh) && kmh > 0 ? String(kmh) : "";
            return this.sortRows(grid);
        });
    }

    // Cells ----------------------------------------------------------------

    onCellChange(rowIndex, cell, ev) {
        // Loads never have thousands, so "," and "." are both the decimal
        // separator: phones often only offer one of them.
        const input = ev.target;
        const text = input.value.trim().replace(/\s*t$/i, "").replace(",", ".");
        let value = null;
        if (text) {
            value = /^\d+(\.\d*)?$|^\.\d+$/.test(text) ? Number(text) : NaN;
            if (!Number.isFinite(value)) {
                // Not a number: leave the stored value and mark the cell.
                input.classList.add("is-invalid");
                return;
            }
        }
        input.classList.remove("is-invalid");
        return this.mutate((grid) => {
            for (let i = cell.start; i < cell.end; i++) {
                grid.rows[rowIndex].values[i] = value;
            }
            return grid;
        });
    }

    // Merged cells ---------------------------------------------------------

    toggleMergeMode() {
        this.state.mergeMode = !this.state.mergeMode;
    }

    /** Join the cell ending at column ``end`` with the next cell.
     * Merging two header cells (e.g. "C3 C4") merges the cells below them
     * too: those categories then have one value in every row. */
    joinRight(rowIndex, end) {
        return this.mutate((grid) => {
            const rows = rowIndex === "header" ? grid.rows : [grid.rows[rowIndex]];
            if (rowIndex === "header") {
                grid.header_joins[end - 1] = true;
            }
            for (const row of rows) {
                row.joins[end - 1] = true;
                // The merged cell keeps the left value (or the right one if empty).
                const value = row.values[end - 1] ?? row.values[end];
                const seg = segments(row.joins, grid.columns.length).find(
                    (s) => s.start < end && s.end > end
                );
                for (let i = seg.start; i < seg.end; i++) {
                    row.values[i] = value;
                }
            }
            return grid;
        });
    }

    split(rowIndex, cell) {
        return this.mutate((grid) => {
            const joins = rowIndex === "header" ? grid.header_joins : grid.rows[rowIndex].joins;
            for (let i = cell.start; i < cell.end - 1; i++) {
                joins[i] = false;
            }
            return grid;
        });
    }
}

export const loadGridField = {
    component: LoadGridField,
    displayName: _t("Load limit raster"),
    supportedTypes: ["json"],
};

registry.category("fields").add("fsm_load_grid", loadGridField);
