"""Standalone checks of fill policy. Does not start Odoo."""
import ast
from pathlib import Path
from types import SimpleNamespace


def run_checks(base_source, workflow_source, order_xml, release_xml):
    tree = ast.parse(base_source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == "FsmRelease")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                  and n.name == "_autofill_vrijgave")
    scope = {"AccessError": PermissionError}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "fill_policy", "exec"), scope)
    fill = scope["_autofill_vrijgave"]

    class Release:
        id = 1
        def __init__(self, state="draft", existing=None, candidates=None):
            self.state = state
            self.data = dict(existing or {})
            self.candidates = dict(candidates or {})
            self.writes = []
        def __getitem__(self, key): return self.data.get(key, False)
        def check_access_rule(self, operation): pass
        def _get_vrijgave_order_defaults(self): return self.candidates
        def flush_recordset(self): pass
        def invalidate_recordset(self): pass
        def with_context(self, **kw): return self
        def write(self, values):
            self.writes.append(dict(values)); self.data.update(values)

    class Records:
        def __init__(self, item, writable=True):
            self.item = item; self.writable = writable
            self.env = SimpleNamespace(context={}, cr=SimpleNamespace(execute=lambda *a: None))
        def check_access_rights(self, *a, **kw): return self.writable
        def sorted(self, key): return [self.item]

    candidate = {"vrijgave_customer_ref": "CLIENT-42", "vrijgave_order_ref": "FO049"}
    draft = Release(candidates=candidate)
    fill(Records(draft))
    assert draft.data == candidate and len(draft.writes) == 1
    fill(Records(draft))
    assert len(draft.writes) == 1
    manual = Release(existing={"vrijgave_customer_ref": "MANUAL"}, candidates=candidate)
    fill(Records(manual))
    assert manual.data["vrijgave_customer_ref"] == "MANUAL"
    assert manual.data["vrijgave_order_ref"] == "FO049"
    frozen = Release(state="released", candidates=candidate)
    fill(Records(frozen)); assert not frozen.writes
    missing = Release(candidates={"vrijgave_customer_ref": False})
    fill(Records(missing)); assert not missing.writes
    viewer = Release(candidates=candidate)
    fill(Records(viewer, writable=False)); assert not viewer.writes

    from xml.etree import ElementTree as ET
    for source in [order_xml, release_xml]:
        root = ET.fromstring(source)
        assert not any("fill" in b.attrib.get("name", "") for b in root.iter("button"))
    assert "sale_id" not in base_source and "sale_id" not in workflow_source
    workflow_tree = ast.parse(workflow_source)
    finalizer = next(n for n in ast.walk(workflow_tree)
                     if isinstance(n, ast.FunctionDef) and n.name == "action_release")
    finalizer_text = ast.get_source_segment(workflow_source, finalizer)
    for helper in ("_prepare_release_equipment_lines", "_prepare_release_contractor_cost_lines",
                   "_prepare_release_timesheet_lines"):
        assert helper in finalizer_text
        assert workflow_source.count(helper) == 1
    for name in ("action_preview_vrijgave", "action_print_vrijgave"):
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert "self._autofill_vrijgave()" in ast.get_source_segment(base_source, method)
    return 9


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "fieldservice_release"
    count = run_checks(
        (root / "models/fsm_release.py").read_text(),
        (root / "models/release_wagon_workflow.py").read_text(),
        (root / "views/release_wagon_views.xml").read_text(),
        (root / "views/fsm_release_views.xml").read_text(),
    )
    print("Passed %s standalone checks" % count)
