/** @odoo-module **/
import { ORM } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

function isPhoneOrTablet() {
    const ua = navigator.userAgent || "";
    const ipadDesktopMode = /Macintosh|MacIntel/i.test(ua + " " + navigator.platform)
        && navigator.maxTouchPoints > 1;
    return /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(ua) || ipadDesktopMode;
}

patch(ORM.prototype, {
    call(model, method, args = [], kwargs = {}) {
        if (model === "fsm.order" && ["get_views", "get_view"].includes(method)) {
            kwargs = {
                ...kwargs,
                context: {
                    ...(kwargs.context || {}),
                    fsm_mobile_scroll: isPhoneOrTablet(),
                },
            };
        }
        return super.call(model, method, args, kwargs);
    },
});
