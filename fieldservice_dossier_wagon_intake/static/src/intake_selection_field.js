/** Inbound inspection: dropdowns in the Findings list open on the first tap.
 *
 * In an editable list, the first click on a row that is not being edited only
 * switches the row to edit mode; the browser's own <select> then needs a second
 * click. The "intake_selection" widget uses Odoo's own dropdown (works on every
 * browser, iPad included) and the list opens it right after that first click.
 */
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ListRenderer } from "@web/views/list/list_renderer";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

const WIDGET = "intake_selection";

export class IntakeSelectionField extends SelectionField {
    static template = "fieldservice_dossier_wagon_intake.IntakeSelectionField";
    static components = { SelectMenu };

    get choices() {
        return this.options.map(([value, label]) => ({ value, label }));
    }

    onSelect(value) {
        this.props.record.update(
            { [this.props.name]: value ?? false },
            { save: this.props.autosave }
        );
    }
}

registry.category("fields").add(WIDGET, {
    ...selectionField,
    component: IntakeSelectionField,
});

patch(ListRenderer.prototype, {
    async onCellClicked(record, column, ev) {
        this._intakeOpenColumn =
            !record.isInEdition && column.type === "field" && column.widget === WIDGET
                ? column.name
                : null;
        return super.onCellClicked(...arguments);
    },

    focusCell(column, forward = true) {
        const result = super.focusCell(...arguments);
        const name = this._intakeOpenColumn;
        this._intakeOpenColumn = null;
        if (name && column && column.name === name) {
            const cell = this.tableRef.el?.querySelector(
                `.o_selected_row td[name="${name}"]`
            );
            cell?.querySelector(".o_select_menu_toggler:not([disabled])")?.click();
        }
        return result;
    },

    onGlobalClick(ev) {
        // Picking an option in the dropdown must not close the edited row.
        if (ev.target.closest?.(".o_select_menu_menu")) {
            return;
        }
        return super.onGlobalClick(...arguments);
    },
});
