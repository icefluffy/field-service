# Copyright 2026 TI-Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Inbound inspections no longer pass or fail: they are only completed.

    Recorded reports (Passed, Passed with remarks, Failed) become Completed and
    their dossier inspection line gets result Not applicable, so a former
    Failed intake no longer blocks dossier approval.
    """
    cr.execute(
        """
        UPDATE fsm_dossier_inspection line
           SET result = 'na'
          FROM fsm_wagon_intake intake
         WHERE intake.inspection_id = line.id
           AND intake.state IN ('passed', 'remarks', 'failed')
           AND line.work_status = 'done'
        """
    )
    cr.execute(
        """
        UPDATE fsm_wagon_intake
           SET state = 'done'
         WHERE state IN ('passed', 'remarks', 'failed')
        """
    )
