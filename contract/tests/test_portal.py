# Copyright 2020 Tecnativa - Víctor Martínez
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

from odoo import http
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestContractPortal(HttpCase, BaseCommon):
    @mute_logger(
        "odoo.addons.contract.tests.test_portal.TestContractPortal.test_tour.browser"
    )
    def test_tour(self):
        partner = self.env["res.partner"].create({"name": "partner test contract"})
        contract = self.env["contract.contract"].create(
            {"name": "Test Contract", "partner_id": partner.id}
        )
        user_portal = self._create_new_portal_user(
            partner_id=partner.id, login="portal_contract", password="portal_contract"
        )
        self.start_tour("/", "contract_portal_tour", login="portal_contract")
        # Contract access
        self.authenticate("portal_contract", "portal_contract")
        http.root.session_store.save(self.session)
        url_contract = (
            f"/my/contracts/{contract.id}?access_token={contract.access_token}"
        )
        self.assertEqual(self.url_open(url=url_contract).status_code, 200)
        contract.message_unsubscribe(partner_ids=user_portal.partner_id.ids)
        self.assertEqual(self.url_open(url=url_contract).status_code, 200)


class TestContractLinePortal(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "service"}
        )
        cls.partner_portal = cls.env["res.partner"].create({"name": "Portal partner"})
        cls.partner_other = cls.env["res.partner"].create({"name": "Other partner"})
        cls.user_portal = cls._create_new_portal_user(
            partner_id=cls.partner_portal.id, login="portal_contract_line"
        )
        cls.contract_portal = cls._create_contract("Own contract", cls.partner_portal)
        cls.contract_other = cls._create_contract("Other contract", cls.partner_other)
        cls.contract_portal.message_subscribe(partner_ids=cls.partner_portal.ids)

    @classmethod
    def _create_contract(cls, name, partner):
        return cls.env["contract.contract"].create(
            {
                "name": name,
                "partner_id": partner.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "name": f"Line of {name}",
                            "quantity": 1,
                            "uom_id": cls.product.uom_id.id,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )

    def test_contract_line_portal_rule(self):
        """Portal users must only read lines of their own contracts."""
        ContractLine = self.env["contract.line"].with_user(self.user_portal)
        lines = ContractLine.search([])
        self.assertEqual(lines, self.contract_portal.contract_line_ids)
        # Reading a line of someone else's contract must be forbidden
        with self.assertRaises(AccessError):
            ContractLine.browse(self.contract_other.contract_line_ids.ids).read(
                ["name"]
            )
