from lxml import etree

SECTIONS = (
    "wheelsets_overview",
    "instructions_page",
    "planning_page",
    "execution_page",
    "activities_page",
    "release_wagon",
)


def scroll_arch(arch):
    root = etree.fromstring(arch.encode() if isinstance(arch, str) else arch)
    notebooks = root.xpath(".//sheet//notebook[not(ancestor::field) and not(ancestor::notebook)]")
    for notebook in notebooks:
        pages = list(notebook)
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
            elif name == "execution_page":
                hidden = etree.Element("div", invisible="True")
                for child in list(page):
                    hidden.append(child)
                page.append(hidden)
                buttons = etree.SubElement(page, "div", attrib={"class": "o_fsm_mobile_time_buttons"})
                etree.SubElement(buttons, "button", name="action_mobile_record_start",
                                 string="Start", type="object", attrib={"class": "btn-primary"},
                                 invisible="date_start or date_end")
                etree.SubElement(buttons, "button", name="action_mobile_record_stop",
                                 string="Stop", type="object", attrib={"class": "btn-secondary"},
                                 invisible="not date_start or date_end")
            if title:
                heading = etree.Element("h2", attrib={"class": "o_fsm_mobile_heading"})
                heading.text = title
                page.insert(0, heading)
        ordered = sorted(pages, key=lambda p: SECTIONS.index(p.get("name"))
                         if p.get("name") in SECTIONS else len(SECTIONS))
        for page in ordered:
            notebook.append(page)
    return etree.tostring(root, encoding="unicode")
