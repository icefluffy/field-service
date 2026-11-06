/** Dropdowns in editable lists open on the first click/tap.
 *
 * In an editable list, the first click on a row that is not being edited only
 * switches that row to edit mode, so a dropdown needed a second click.
 *
 * - Selection fields (and many2one fields shown with widget="selection") in
 *   lists use Odoo's own dropdown instead of the browser's <select>. Odoo can
 *   open it itself, which works on every browser, iPad/Safari included.
 * - Right after a click switches a row to edit mode, the dropdown of the
 *   clicked cell is opened: the selection dropdown, or the suggestion list of
 *   a many2one / tags field.
 */
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ListRenderer } from "@web/views/list/list_renderer";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class ListSelectMenuField extends SelectionField {
    static template = "web_list_dropdown_one_click.ListSelectMenuField";
    static components = { SelectMenu };

    get choices() {
        return this.options.map(([value, label]) => ({ value, label }));
    }

    onSelect(value) {
        let newValue = value ?? false;
        if (this.type === "many2one" && newValue !== false) {
            newValue = this.options.find((o) => o[0] === newValue) || false;
        }
        this.props.record.update(
            { [this.props.name]: newValue },
            { save: this.props.autosave }
        );
    }
}

// "list." prefix: only used inside list views; forms keep the standard field.
registry.category("fields").add("list.selection", {
    ...selectionField,
    component: ListSelectMenuField,
});

const OPENERS = [
    ".o_select_menu_toggler:not([disabled])",
    "input.o-autocomplete--input:not([readonly]):not([disabled])",
];

patch(ListRenderer.prototype, {
    async onCellClicked(record, column, ev) {
        this._oneClickColumn =
            !record.isInEdition && column.type === "field" ? column.name : null;
        return super.onCellClicked(...arguments);
    },

    focusCell(column, forward = true) {
        const result = super.focusCell(...arguments);
        const name = this._oneClickColumn;
        this._oneClickColumn = null;
        if (name && column && column.name === name) {
            const cell = this.tableRef.el?.querySelector(
                `.o_selected_row td[name="${name}"]`
            );
            for (const selector of OPENERS) {
                const opener = cell?.querySelector(selector);
                if (opener) {
                    opener.click();
                    break;
                }
            }
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
