# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Name the wheelset inspection type after the paper form.

    The type is loaded with noupdate, so a database that still has the
    original name "Wielstelrapport" keeps it. A name changed by hand to
    anything else is left alone.
    """
    wsr = env.ref("fieldservice_dossier.inspection_type_wsr", raise_if_not_found=False)
    if wsr and (wsr.name or "").strip().lower() == "wielstelrapport":
        wsr.name = "Opname Wielstellen"
