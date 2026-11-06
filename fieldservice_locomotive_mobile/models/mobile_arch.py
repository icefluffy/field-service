# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree

SECTIONS = (
    "wheelsets_overview",
    "instructions_page",
    "planning_page",
    "execution_page",
    "activities_page",
    "release_wagon",
)

# Fields of the order header area that are not shown on phones/tablets.
HIDDEN_HEADER_FIELDS = (
    "customer_reference",
    "template_id",
    "team_id",
    "vehicle_id",
    "dossier_id",
    "tag_ids",
    "fsm_code_ids",  # damage codes
)


# Buttons not shown on phones/tablets.
HIDDEN_BUTTONS = ("action_preview_workorder", "action_print_workorder")


def _outside_notebook_and_subviews(node):
    return not node.xpath("ancestor::notebook or ancestor::field")


def _adapt_header(root):
    sheet_fields = [
        f for f in root.xpath(".//sheet//field")
        if _outside_notebook_and_subviews(f)
    ]
    # Hide unwanted fields (they stay loaded, only not displayed).
    for field in sheet_fields:
        if field.get("name") in HIDDEN_HEADER_FIELDS:
            field.set("invisible", "True")
            field.attrib.pop("required", None)
    for button in root.xpath(".//button"):
        if button.get("name") in HIDDEN_BUTTONS and not button.xpath("ancestor::field"):
            button.set("invisible", "True")
    # Put the Navigate button directly under Track.
    tracks = [
        f for f in sheet_fields
        if f.get("name") == "track" and f.get("invisible") not in ("1", "True")
    ]
    buttons = [
        b for b in root.xpath(".//sheet//button[@name='action_open_google_maps']")
        if _outside_notebook_and_subviews(b)
    ]
    if tracks and buttons:
        anchor = tracks[0]
        for button in buttons:
            button.getparent().remove(button)
            anchor.addnext(button)
            anchor = button


def _stop_button(parent):
    return etree.SubElement(
        parent, "button", name="action_mobile_record_stop",
        string="Stop", type="object", attrib={"class": "btn-danger"},
        invisible="not date_start or date_end",
    )


def scroll_arch(arch):
    root = etree.fromstring(arch.encode() if isinstance(arch, str) else arch)
    _adapt_header(root)
    notebooks = root.xpath(".//sheet//notebook[not(ancestor::field) and not(ancestor::notebook)]")
    for notebook in notebooks:
        pages = list(notebook)
        names = {p.get("name") for p in pages if p.tag == "page"}
        has_activities = "activities_page" in names
        has_execution = "execution_page" in names
        notebook.tag = "div"
        notebook.set("class", "o_fsm_mobile_scroll")
        for page in pages:
            if page.tag != "page":
                continue
            name = page.get("name", "")
            title = page.get("string", "")
            page.tag = "div"
            page.attrib.pop("string", None)
            page.set("class", "o_fsm_mobile_section")
            if name not in SECTIONS:
                page.set("invisible", "True")
                continue
            if name == "wheelsets_overview":
                buttons = page.xpath(".//button[@name='action_open_equipment']")
                for button in buttons:
                    button.getparent().remove(button)
                hidden = etree.Element("div", invisible="True")
                for child in list(page):
                    hidden.append(child)
                page.append(hidden)
                for button in buttons:
                    page.append(button)
            elif name == "planning_page":
                targets = page.xpath(".//field[@name='scheduled_date_start']")
                for field in targets:
                    field.getparent().remove(field)
                hidden = etree.Element("div", invisible="True")
                for child in list(page):
                    hidden.append(child)
                page.append(hidden)
                group = etree.SubElement(page, "group")
                for field in targets:
                    group.append(field)
            elif name == "activities_page":
                for listing in page.xpath(".//field[@name='order_activity_ids']/list"):
                    listing.set("editable", "bottom")
                    for field in listing.findall("field"):
                        if field.get("name") not in ("name", "quantity"):
                            field.set("column_invisible", "True")
                    for button in listing.findall("button"):
                        if button.get("name") != "action_done":
                            button.set("invisible", "True")
                # Stop comes after the Activities section.
                if has_execution:
                    stop_box = etree.SubElement(
                        page, "div", attrib={"class": "o_fsm_mobile_time_buttons"}
                    )
                    _stop_button(stop_box)
            elif name == "execution_page":
                hidden = etree.Element("div", invisible="True")
                for child in list(page):
                    hidden.append(child)
                page.append(hidden)
                buttons = etree.SubElement(page, "div", attrib={"class": "o_fsm_mobile_time_buttons"})
                etree.SubElement(buttons, "button", name="action_mobile_record_start",
                                 string="Start", type="object", attrib={"class": "btn-success"},
                                 invisible="date_start or date_end")
                if not has_activities:
                    _stop_button(buttons)
            if title:
                heading = etree.Element("h2", attrib={"class": "o_fsm_mobile_heading"})
                heading.text = title
                page.insert(0, heading)
        ordered = sorted(pages, key=lambda p: SECTIONS.index(p.get("name"))
                         if p.get("name") in SECTIONS else len(SECTIONS))
        for page in ordered:
            notebook.append(page)
    return etree.tostring(root, encoding="unicode")
