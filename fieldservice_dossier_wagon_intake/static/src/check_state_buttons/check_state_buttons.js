/** @odoo-module **/
// Copyright 2026 TI-Consulting
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
//
// Assessment buttons on the finding cards of the Inbound inspection (phone
// layout). OK and Not applicable are set right on the card; Defect is set and
// then the finding opens full screen to enter the defect and quantity.
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const OPEN_STATES = ["draft", "progress"];

const CHOICES = [
    { value: "ok", btnClass: "btn-success", outlineClass: "btn-outline-success" },
    { value: "defect", btnClass: "btn-danger", outlineClass: "btn-outline-danger" },
    { value: "na", btnClass: "o_fsm_btn_na_active", outlineClass: "o_fsm_btn_na" },
];

export class CheckStateButtons extends Component {
    static template = "fieldservice_dossier_wagon_intake.CheckStateButtons";
    static props = { ...standardFieldProps };

    get value() {
        return this.props.record.data[this.props.name];
    }

    /**
     * Fields on one2many kanban cards are always passed as readonly, so the
     * lock follows the inspection itself: only open inspections can be edited.
     */
    get isLocked() {
        const parent = this.props.record.evalContext.parent;
        return parent ? !OPEN_STATES.includes(parent.state) : this.props.readonly;
    }

    get choices() {
        const labels = Object.fromEntries(
            this.props.record.fields[this.props.name].selection
        );
        return CHOICES.map((choice) => ({
            ...choice,
            // "Not applicable" is too long for three buttons on a phone.
            label: choice.value === "na" ? _t("N/A") : labels[choice.value],
            title: labels[choice.value],
        }));
    }

    /**
     * Open the finding in its form, exactly like tapping the card.
     * The kanban card component owns openRecord; walk up to it. Fall back to
     * a click on the card element.
     */
    openFinding(card) {
        let node = this.__owl__.parent;
        while (node) {
            const props = node.component && node.component.props;
            if (props && typeof props.openRecord === "function" && props.record?.id === this.props.record.id) {
                return props.openRecord(props.record);
            }
            node = node.parent;
        }
        card?.click();
    }

    async onClick(ev, value) {
        if (this.isLocked) {
            return;
        }
        const card = ev.currentTarget.closest(".o_kanban_record");
        if (this.value !== value) {
            const changes = { [this.props.name]: value };
            // A defect needs a quantity of at least 1; start from 1.
            if (value === "defect" && !(this.props.record.data.quantity > 0)) {
                changes.quantity = 1;
            }
            // Leaving Defect: the defect text and quantity no longer apply.
            if (this.value === "defect" && value !== "defect") {
                changes.defect = false;
                changes.quantity = 0;
            }
            await this.props.record.update(changes);
        }
        if (value === "defect") {
            this.openFinding(card);
        }
    }
}

export const checkStateButtons = {
    component: CheckStateButtons,
    displayName: _t("Assessment buttons"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("fsm_check_state_buttons", checkStateButtons);
