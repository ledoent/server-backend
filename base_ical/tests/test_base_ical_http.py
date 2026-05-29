# Copyright 2023 Hunki Enterprises BV
# Copyright 2024 initOS GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo.tests.common import HttpCase


class TestBaseIcalHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Build a self-contained fixture instead of relying on demo data,
        # which OCA CI does not load (env.ref on a demo xmlid would fail).
        cls.calendar = cls.env["base.ical"].create(
            {
                "name": "Demo calendar",
                "model_id": cls.env.ref("base.model_res_users").id,
                "expression_uid": "str(record.id)",
                "expression_dtstart": "record.create_date",
                "expression_dtend": "record.write_date",
            }
        )
        cls.user = cls.env.ref("base.user_admin")
        desc = (
            cls.env["base.ical.url.description"]
            .with_user(cls.user)
            .create({"calendar_id": cls.calendar.id, "name": "Testing"})
        )
        cls.calendar_url = desc._make_url()

    def test_calendar_retrieval(self):
        response = self.url_open(self.calendar_url)
        self.assertTrue(response.ok)
        self.assertTrue(response.text.startswith("BEGIN:VCALENDAR"))
