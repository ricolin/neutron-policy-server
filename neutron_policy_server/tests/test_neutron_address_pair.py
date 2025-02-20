# SPDX-License-Identifier: Apache-2.0

from copy import deepcopy

import pytest
from neutron.tests.unit.db import test_allowedaddresspairs_db as base_test
from neutron_lib.api.definitions import allowedaddresspairs as addr_apidef
from oslo_config import cfg
from oslo_db import options as db_options

from neutron_policy_server import wsgi
from neutron_policy_server.tests import test


class TestAddressPairCasesFlaskBase(
    test.TestCase, base_test.AllowedAddressPairDBTestCase
):

    def setUp(self, plugin=None, ext_mgr=None):
        super(TestAddressPairCasesFlaskBase, self).setUp(plugin)
        address_pairs = [{"mac_address": "00:00:00:00:00:01", "ip_address": "10.0.0.1"}]
        db_options.set_defaults(cfg.CONF, connection="sqlite://")

        with self.network() as net:
            with self.subnet(network=net, cidr="10.0.0.0/24") as subnet:
                fixed_ips = [
                    {"subnet_id": subnet["subnet"]["id"], "ip_address": "10.0.0.1"}
                ]

            self.port_resp = self._create_port(
                self.fmt,
                net["network"]["id"],
                mac_address="00:00:00:00:00:01",
                fixed_ips=fixed_ips,
            )
            self.port = self.deserialize(self.fmt, self.port_resp)

            self.port_resp_dep = self._create_port(
                self.fmt,
                net["network"]["id"],
                arg_list=(addr_apidef.ADDRESS_PAIRS,),
                allowed_address_pairs=address_pairs,
            )
            self.port_dep = self.deserialize(self.fmt, self.port_resp_dep)

        # delete
        self.delete_port_json = {
            "rule": "delete_port",
            "target": self.port["port"],
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port["port"]["project_id"],
            },
        }
        self.delete_port_dep_json = {
            "rule": "delete_port",
            "target": self.port_dep["port"],
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }

        # update
        self.update_port_no_address = {
            "rule": "update_port",
            "target": self.port["port"].copy(),
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }
        self.update_port_no_address["target"]["attributes_to_update"] = ["name"]
        self.update_port_no_address["target"]["name"] = "new_name"

        self.update_port_not_exist = {
            "rule": "update_port",
            "target": self.port_dep["port"].copy(),
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }
        self.update_port_not_exist["target"]["attributes_to_update"] = ["mac_address"]
        self.update_port_not_exist["target"][
            "id"
        ] = "52c5a95c-9310-4993-a731-89cfd5a41fd9"

        self.update_port_dep = {
            "rule": "update_port",
            "target": self.port_dep["port"].copy(),
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }
        self.update_port_dep["target"]["attributes_to_update"] = ["mac_address"]
        self.update_port_dep["target"]["mac_address"] = "52:54:00:41:a4:97"

        self.update_port = {
            "rule": "update_port",
            "target": self.port["port"].copy(),
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }
        self.update_port["target"]["attributes_to_update"] = ["mac_address"]
        self.update_port["target"]["mac_address"] = "52:54:00:41:a4:97"

        self.allowed_address_pairs = {
            "rule": "allowed_address_pairs",
            "target": self.port_dep["port"].copy(),
            "credentials": {
                "user_id": "fake_user",
                "project_id": self.port_dep["port"]["project_id"],
            },
        }
        self.allowed_address_pairs["target"]["attributes_to_update"] = [
            "allowed_address_pairs"
        ]
        self.allowed_address_pairs["target"]["allowed_address_pairs"] = [
            {"mac_address": "00:00:00:00:00:01", "ip_address": "10.0.0.1"}
        ]
        self.allowed_address_pairs_not_found = deepcopy(self.allowed_address_pairs)
        self.allowed_address_pairs_not_found["target"]["allowed_address_pairs"] = [
            {"ip_address": "10.96.250.203", "mac_address": "fa:16:3e:da:ed:0b"}
        ]
        self.allowed_address_pairs_address_not_found = deepcopy(
            self.allowed_address_pairs
        )
        self.allowed_address_pairs_address_not_found["target"]["allowed_address_pairs"][
            0
        ]["ip_address"] = "10.96.250.203"
        self.allowed_address_pairs_no_attribute = deepcopy(self.allowed_address_pairs)
        self.allowed_address_pairs_no_attribute["target"]["attributes_to_update"] = []
        self.allowed_address_pairs_not_in_attribute = deepcopy(
            self.allowed_address_pairs
        )
        self.allowed_address_pairs_not_in_attribute["target"][
            "attributes_to_update"
        ] = ["mac_address"]

        self.allowed_address_pairs_empty = deepcopy(self.allowed_address_pairs)
        self.allowed_address_pairs_empty["target"]["allowed_address_pairs"] = []

        self.allowed_address_pairs_target_not_found = deepcopy(
            self.allowed_address_pairs
        )
        self.allowed_address_pairs_target_not_found["target"]["id"] = "foo"

    @pytest.fixture()
    def app(
        self,
    ):
        app = wsgi.create_app()
        yield app

    @pytest.fixture()
    def client(self, app):
        return app.test_client()

    @pytest.fixture()
    def runner(self, app):
        return app.test_cli_runner()


@pytest.mark.usefixtures("client_class")
class TestAddressPairCasesFlask(TestAddressPairCasesFlaskBase):

    def test_port_delete_success(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-delete", json=self.delete_port_dep_json
        )  # pylint: disable=E1101
        self.assertEqual(b"True", response.data)
        self.assertEqual(200, response.status_code)

    def test_port_delete_fail_with_dep(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-delete", json=self.delete_port_json
        )  # pylint: disable=E1101
        self.assertEqual(
            bytes(
                (
                    "Address pairs dependency found for port: "
                    f"{self.port['port']['id']}"
                ),
                "utf-8",
            ),
            response.data,
        )
        self.assertEqual(403, response.status_code)

    def test_port_update_success(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-update", json=self.update_port_dep
        )  # pylint: disable=E1101
        self.assertEqual(b"True", response.data)
        self.assertEqual(200, response.status_code)

    def test_port_update_success_no_address_change(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-update", json=self.update_port_no_address
        )  # pylint: disable=E1101
        self.assertEqual(b"True", response.data)
        self.assertEqual(200, response.status_code)

    def test_port_update_fail_no_match_port(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-update", json=self.update_port_not_exist
        )  # pylint: disable=E1101
        self.assertEqual(b"True", response.data)
        self.assertEqual(200, response.status_code)

    def test_port_update_fail(self):
        response = self.client.post(  # pylint: disable=E1101
            "/port-update", json=self.update_port
        )
        self.assertEqual(
            bytes(
                (
                    "Address pairs dependency found for port: "
                    f"{self.port['port']['id']}"
                ),
                "utf-8",
            ),
            response.data,
        )
        self.assertEqual(403, response.status_code)

    def test_health_check_success(self):
        response = self.client.get("/health")  # pylint: disable=E1101
        self.assertEqual(200, response.status_code)

    def test_address_pair_success(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs
        )
        self.assertEqual(
            b"True",
            response.data,
        )
        self.assertEqual(200, response.status_code)

    def test_address_pair_success_no_attributes_to_update(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_no_attribute
        )
        self.assertEqual(
            b"True",
            response.data,
        )
        self.assertEqual(200, response.status_code)

    def test_address_pair_success_empty(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_empty
        )
        self.assertEqual(
            b"True",
            response.data,
        )
        self.assertEqual(200, response.status_code)

    def test_address_pair_success_not_in_attributes(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_not_in_attribute
        )
        self.assertEqual(
            b"True",
            response.data,
        )
        self.assertEqual(200, response.status_code)

    def test_address_pair_fail_target_not_found(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_target_not_found
        )
        portname = self.allowed_address_pairs_target_not_found["target"]["id"]
        self.assertEqual(
            f"Can't fetch port {portname} with current context, skip this check.".encode(
                "utf-8"
            ),
            response.data,
        )
        self.assertEqual(403, response.status_code)

    def test_address_pair_fail_mac_not_found(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_not_found
        )
        self.assertEqual(
            b"Zero or Multiple match port found with MAC address fa:16:3e:da:ed:0b.",
            response.data,
        )
        self.assertEqual(403, response.status_code)

    def test_address_pair_fail_address_not_found(self):
        response = self.client.post(  # pylint: disable=E1101
            "/address-pair", json=self.allowed_address_pairs_address_not_found
        )
        self.assertEqual(
            f"IP address not exists in network from project {self.port['port']['project_id']}.".encode(
                "utf-8"
            ),
            response.data,
        )
        self.assertEqual(403, response.status_code)
