from galaxy_ng.app.access_control.statements.insights import (
    INSIGHTS_STATEMENTS,
    _INSIGHTS_STATEMENTS
)
from galaxy_ng.tests.unit.api.base import BaseTestCase


class TestInisightsStatements(BaseTestCase):
    def test_transformed_statement_is_correct(self):
        for view in _INSIGHTS_STATEMENTS:
            self.assertIn(view, INSIGHTS_STATEMENTS)

            for statement in INSIGHTS_STATEMENTS[view]:
                condition = statement.get("condition", [])
                if statement["effect"] == "deny":
                    self.assertNotIn("has_rh_entitlements", condition)
                else:
                    self.assertIn("has_rh_entitlements", condition)
