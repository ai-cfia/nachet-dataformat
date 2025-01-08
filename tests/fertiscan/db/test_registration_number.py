"""
This is a test script for the database packages.
It tests the functions in the registration number modules.
"""

import os
import unittest
import json

import datastore.db as db
from datastore.db.metadata import validator
from fertiscan.db.metadata.inspection import RegistrationNumber
from fertiscan.db.queries import label, registration_number

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class test_registration_number(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.registration_number = "123456"

        self.lot_number = "lot_number"
        self.product_name = "product_name"
        self.npk = "npk"
        self.registration_number = "registration_number"
        self.n = 10.0
        self.p = 20.0
        self.k = 30.0
        self.weight = None
        self.density = None
        self.volume = None
        self.warranty = "warranty"
        self.label_id = label.new_label_information(
            self.cursor,
            self.product_name,
            self.lot_number,
            self.npk,
            self.n,
            self.p,
            self.k,
            None,
            None,
            False,
            None,
        )

        self.is_an_ingredient = False
        self.read_name = "read_name"
        self.edited = False

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_registration_number(self):
        registration_number_id = registration_number.new_registration_number(
            self.cursor,
            self.registration_number,
            self.label_id,
            self.is_an_ingredient,
            self.read_name,
            self.edited,
        )
        self.assertTrue(validator.is_valid_uuid(registration_number_id))

    def test_get_registration_numbers_json(self):
        registration_number.new_registration_number(
            self.cursor,
            self.registration_number,
            self.label_id,
            self.is_an_ingredient,
            self.read_name,
            self.edited,
        )
        registration_numbers = registration_number.get_registration_numbers_json(
            self.cursor, self.label_id
        )
        RegistrationNumber.model_validate(registration_numbers)
        self.assertEqual(len(registration_numbers), 1)

    def test_get_registration_numbers_json_empty(self):
        registration_numbers = registration_number.get_registration_numbers_json(
            self.cursor, self.label_id
        )
        RegistrationNumber.model_validate(registration_numbers)
        print(registration_numbers)
        self.assertEqual(len(registration_numbers["registration_numbers"]), 0)

    def test_update_registration_number(self):
        registration_number.new_registration_number(
            self.cursor,
            self.registration_number,
            self.label_id,
            self.is_an_ingredient,
            self.read_name,
            self.edited,
        )
        old_data = registration_number.get_registration_numbers_json(
            self.cursor, self.label_id
        )
        self.assertEqual(
            old_data["registration_numbers"][0]["registration_number"],
            self.registration_number,
        )
        new_reg_number = "654321"
        new_dict = old_data["registration_numbers"]
        new_dict[0]["registration_number"] = new_reg_number

        registration_number.update_registration_number(
            self.cursor,
            json.dumps(new_dict),
            self.label_id,
        )
        new_data = registration_number.get_registration_numbers_json(
            self.cursor, self.label_id
        )

        self.assertEqual(
            new_data["registration_numbers"][0]["registration_number"], new_reg_number
        )
        self.assertNotEqual(
            new_data["registration_numbers"][0]["registration_number"],
            self.registration_number,
        )
