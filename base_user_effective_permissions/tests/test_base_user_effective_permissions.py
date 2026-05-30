# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)


from odoo.tests.common import TransactionCase


class EffectivePermissionsCase(TransactionCase):
    def test_effective_permissions(self):
        """Test effective permissions of an internal user."""
        # Demo data is not loaded on OCA CI; create an internal user instead.
        user = self.env["res.users"].create(
            {
                "name": "Effective Perm Test User",
                "login": "effective_perm_test_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        action = user.action_show_effective_permissions()
        permissions = self.env["res.users.effective.permission"].search(
            action["domain"]
        )
        self.assertTrue(
            permissions.filtered(
                lambda x: x.model_name == "res.company"
            ).read_permission
        )
