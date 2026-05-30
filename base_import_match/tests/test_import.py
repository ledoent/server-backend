# Copyright 2016 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

OPTIONS = {
    "headers": True,
    "quoting": '"',
    "separator": ",",
}


class ImportCase(TransactionCase):
    @classmethod
    def _create_match(cls, sequence, field_xmlids):
        match = cls.env["base_import.match"].create(
            {
                "model_id": cls.env.ref("base.model_res_partner").id,
                "sequence": sequence,
            }
        )
        for field_xmlid in field_xmlids:
            cls.env["base_import.match.field"].create(
                {"match_id": match.id, "field_id": cls.env.ref(field_xmlid).id}
            )
        return match

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Demo data is not loaded on OCA CI (--without-demo=all). Recreate the
        # partners/user the tests match against, plus the email/name/parent
        # match rules that live in demo/ (data/ already provides vat + login).
        Partner = cls.env["res.partner"]
        cls.deco_addict = Partner.create({"name": "Deco Addict", "is_company": True})
        cls.gemini = Partner.create({"name": "Gemini Furniture", "is_company": True})
        cls.floyd = Partner.create(
            {
                "name": "Floyd Steward",
                "function": "Original Function",
                "email": "floyd.steward34@example.com",
                "parent_id": cls.deco_addict.id,
            }
        )
        cls.env["ir.model.data"].create(
            [
                {
                    "module": "base_import_match",
                    "name": "imd_deco_addict",
                    "model": "res.partner",
                    "res_id": cls.deco_addict.id,
                },
                {
                    "module": "base_import_match",
                    "name": "imd_gemini",
                    "model": "res.partner",
                    "res_id": cls.gemini.id,
                },
            ]
        )
        cls.user = cls.env["res.users"].create(
            {"name": "Demo User", "login": "base_import_match_demo"}
        )
        # name + parent_id + is_company
        cls._create_match(
            20,
            [
                "base.field_res_partner__name",
                "base.field_res_partner__parent_id",
                "base.field_res_partner__is_company",
            ],
        )
        # email
        cls._create_match(30, ["base.field_res_partner__email"])
        # name
        cls._create_match(40, ["base.field_res_partner__name"])

    def _import(self, res_model, content):
        """Create and return a ``base_import.import`` record from raw CSV text."""
        return self.env["base_import.import"].create(
            {
                "res_model": res_model,
                "file": content,
                "file_name": "test.csv",
                "file_type": "csv",
            }
        )

    def test_res_partner_external_id(self):
        """Change name based on External ID."""
        content = (
            "base_import_match.imd_deco_addict,BE077777777,"
            "Deco Addict External ID Changed"
        )
        record = self._import("res.partner", content)
        record.execute_import(["id", "vat", "name"], [], OPTIONS)
        self.deco_addict.invalidate_recordset()
        self.assertEqual(self.deco_addict.name, "Deco Addict External ID Changed")

    def test_res_partner_dbid(self):
        """Change name based on DB ID."""
        content = (
            f"{self.deco_addict.id},BE0999999999,Deco Addict External DBID Changed\n"
            f"{self.gemini.id},BE0888888888,Gemini Furniture External DBID Changed"
        )
        record = self._import("res.partner", content)
        record.execute_import([".id", "vat", "name"], [], OPTIONS)
        self.deco_addict.invalidate_recordset()
        self.gemini.invalidate_recordset()
        self.assertEqual(self.deco_addict.name, "Deco Addict External DBID Changed")
        self.assertEqual(self.gemini.name, "Gemini Furniture External DBID Changed")

    def test_res_partner_vat(self):
        """Change name based on VAT."""
        self.deco_addict.vat = "BE0477472701"
        content = "Deco Addict Changed,BE0477472701,True"
        record = self._import("res.partner", content)
        record.execute_import(["name", "vat", "is_company"], [], OPTIONS)
        self.deco_addict.invalidate_recordset()
        self.assertEqual(self.deco_addict.name, "Deco Addict Changed")

    def test_res_partner_invalid_combination_vat(self):
        """is_company=False breaks the conditional vat rule: no match."""
        self.deco_addict.vat = "BE0477472701"
        original_name = self.deco_addict.name
        content = "Deco Addict Changed,BE0477472701,False"
        record = self._import("res.partner", content)
        record.execute_import(["name", "vat", "is_company"], [], OPTIONS)
        self.deco_addict.invalidate_recordset()
        self.assertEqual(self.deco_addict.name, original_name)

    def test_res_partner_parent_name_is_company(self):
        """Change email based on parent_id, name and is_company."""
        content = (
            "Floyd Steward,False,base_import_match.imd_deco_addict,"
            "floyd.steward34.changed@example.com"
        )
        record = self._import("res.partner", content)
        record.execute_import(
            ["name", "is_company", "parent_id/id", "email"], [], OPTIONS
        )
        self.floyd.invalidate_recordset()
        self.assertEqual(self.floyd.email, "floyd.steward34.changed@example.com")

    def test_res_partner_email(self):
        """Change name based on email."""
        content = "floyd.steward34@example.com,Floyd Steward Changed"
        record = self._import("res.partner", content)
        record.execute_import(["email", "name"], [], OPTIONS)
        self.floyd.invalidate_recordset()
        self.assertEqual(self.floyd.name, "Floyd Steward Changed")

    def test_res_partner_name(self):
        """Change function based on name."""
        content = "Function Changed,Floyd Steward"
        record = self._import("res.partner", content)
        record.execute_import(["function", "name"], [], OPTIONS)
        self.floyd.invalidate_recordset()
        self.assertEqual(self.floyd.function, "Function Changed")

    def test_res_partner_name_duplicated(self):
        """Duplicate names: the email rule disambiguates, the name rule skips."""
        self.deco_addict.name = self.floyd.name
        self.deco_addict.email = "unique@example.com"
        original_function = self.floyd.function
        content = "Function Changed,Floyd Steward,unique@example.com"
        record = self._import("res.partner", content)
        record.execute_import(["function", "name", "email"], [], OPTIONS)
        self.floyd.invalidate_recordset()
        self.deco_addict.invalidate_recordset()
        self.assertEqual(self.floyd.function, original_function)
        self.assertEqual(self.deco_addict.function, "Function Changed")

    def test_res_users_login(self):
        """Change name based on login."""
        content = "base_import_match_demo,Demo User Changed"
        record = self._import("res.users", content)
        record.execute_import(["login", "name"], [], OPTIONS)
        self.user.invalidate_recordset()
        self.assertEqual(self.user.name, "Demo User Changed")
