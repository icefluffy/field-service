/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MediaPlugin } from "@html_editor/main/media/media_plugin";

patch(MediaPlugin.prototype, {
    onSaveMediaDialog(element, { node }) {
        const { resModel } = this.recordInfo;

        // Only apply this behavior to FSM order resolutions.
        const isResolution = resModel === "fsm.order";

        if (!isResolution || node) {
            super.onSaveMediaDialog(element, { node });
            return;
        }

        // Insert the media using the standard Odoo behavior.
        this.dependencies.dom.insert(element);

        // Add a line break after the newly inserted media.
        const br = this.document.createElement("br");
        element.after(br);

        // Put the cursor after the line break.
        this.dependencies.selection.setSelection({
            anchorNode: element.parentNode,
            anchorOffset: Array.from(element.parentNode.childNodes).indexOf(br) + 1,
        });

        this.dependencies.history.addStep();
    },
});