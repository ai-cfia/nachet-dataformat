"""
This is a test script for the database packages.
It tests the functions in the user, seed and picture modules.
"""

import os
import unittest

import datastore.db as db
from datastore.db.metadata import validator
from fertiscan.db.metadata import inspection as metadata
from fertiscan.db.queries import errors as e
from fertiscan.db.queries import label, nutrients

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class test_element(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.element_name_fr = "test-nutriment"
        self.element_name_en = "test-nutrient"
        self.element_symbol = "Xy"
        self.element_number = 700

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_element(self):
        element_id = nutrients.new_element(
            self.cursor,
            self.element_number,
            self.element_name_fr,
            self.element_name_en,
            self.element_symbol,
        )
        self.assertIsInstance(element_id, int)

    def test_get_element_id(self):
        element_id = nutrients.new_element(
            self.cursor,
            self.element_number,
            self.element_name_fr,
            self.element_name_en,
            self.element_symbol,
        )
        self.assertEqual(
            nutrients.get_element_id_full_search(self.cursor, self.element_symbol),
            element_id,
        )
        self.assertEqual(
            nutrients.get_element_id_full_search(self.cursor, self.element_name_fr),
            element_id,
        )
        self.assertEqual(
            nutrients.get_element_id_full_search(self.cursor, self.element_name_en),
            element_id,
        )
        self.assertEqual(
            nutrients.get_element_id_name(self.cursor, self.element_name_fr), element_id
        )
        self.assertEqual(
            nutrients.get_element_id_name(self.cursor, self.element_name_en), element_id
        )
        self.assertEqual(
            nutrients.get_element_id_symbol(self.cursor, self.element_symbol),
            element_id,
        )

    def test_get_element_error(self):
        self.assertRaises(
            e.ElementCompoundNotFoundError,
            nutrients.get_element_id_full_search,
            self.cursor,
            "not-an-element",
        )
        self.assertRaises(
            e.ElementCompoundNotFoundError,
            nutrients.get_element_id_name,
            self.cursor,
            "not-an-element",
        )
        self.assertRaises(
            e.ElementCompoundNotFoundError,
            nutrients.get_element_id_symbol,
            self.cursor,
            "not-an-element",
        )


class test_guaranteed_analysis(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.element_name_fr = "test-nutriment"
        self.element_name_en = "test-nutrient"
        self.element_symbol = "Xy"
        self.element_number = 700
        self.element_id = nutrients.new_element(
            self.cursor,
            self.element_number,
            self.element_name_fr,
            self.element_name_en,
            self.element_symbol,
        )

        self.guaranteed_analysis_name = "test-micronutrient"
        self.guaranteed_analysis_value = 10
        self.guaranteed_analysis_unit = "%"

        self.title_en = "title_en"
        self.title_fr = "title_fr"
        self.is_minimal = False

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

        self.label_information_id = label.new_label_information(
            self.cursor,
            self.product_name,
            self.lot_number,
            self.npk,
            self.n,
            self.p,
            self.k,
            self.title_en,
            self.title_fr,
            self.is_minimal,
            None,
        )
        self.language = "fr"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_guaranteed_analysis(self):
        guaranteed_analysis_id = nutrients.new_guaranteed_analysis(
            self.cursor,
            self.guaranteed_analysis_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        self.assertTrue(validator.is_valid_uuid(guaranteed_analysis_id))

    def test_new_guaranteed_analysis_empty(self):
        with self.assertRaises(e.GuaranteedAnalysisCreationError):
            nutrients.new_guaranteed_analysis(
                self.cursor,
                None,
                None,
                None,
                self.label_information_id,
                self.language,
                self.element_id,
                False,
            )

    def test_get_guaranteed_analysis_json(self):
        nutrients.new_guaranteed_analysis(
            self.cursor,
            self.guaranteed_analysis_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        data = nutrients.get_guaranteed_analysis_json(
            self.cursor, label_id=self.label_information_id
        )
        data = metadata.GuaranteedAnalysis.model_validate(data)
        self.assertEqual(
            data.fr[0].name,
            self.guaranteed_analysis_name,
        )
        self.assertIsNotNone(data)

    def test_get_guaranteed_analysis_json_empty(self):
        data = nutrients.get_guaranteed_analysis_json(
            self.cursor, label_id=self.label_information_id
        )
        data = metadata.GuaranteedAnalysis.model_validate(data)
        self.assertIsNotNone(data.title)
        self.assertIsNotNone(data.title.en)

    def test_get_guaranteed_analysis(self):
        guaranteed_analysis_id = nutrients.new_guaranteed_analysis(
            self.cursor,
            self.guaranteed_analysis_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        guaranteed_analysis_data = nutrients.get_guaranteed(
            self.cursor, guaranteed_analysis_id
        )
        self.assertEqual(guaranteed_analysis_data[0], self.guaranteed_analysis_name)
        self.assertEqual(guaranteed_analysis_data[1], self.guaranteed_analysis_value)
        self.assertEqual(guaranteed_analysis_data[2], self.guaranteed_analysis_unit)
        self.assertEqual(guaranteed_analysis_data[3], self.element_id)
        self.assertEqual(guaranteed_analysis_data[4], self.label_information_id)
        self.assertFalse(guaranteed_analysis_data[5])
        self.assertEqual(guaranteed_analysis_data[6], self.language)
        self.assertEqual(
            guaranteed_analysis_data[7],
            (
                self.guaranteed_analysis_name
                + " "
                + str(self.guaranteed_analysis_value)
                + " "
                + self.guaranteed_analysis_unit
            ),
        )

    def test_get_full_guaranteed_analysis(self):
        guaranteed_analysis_id = nutrients.new_guaranteed_analysis(
            self.cursor,
            self.guaranteed_analysis_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        guaranteed_analysis_data = nutrients.get_full_guaranteed(
            self.cursor, guaranteed_analysis_id
        )
        self.assertEqual(guaranteed_analysis_data[0], self.guaranteed_analysis_name)
        self.assertEqual(guaranteed_analysis_data[1], self.guaranteed_analysis_value)
        self.assertEqual(guaranteed_analysis_data[2], self.guaranteed_analysis_unit)
        self.assertEqual(guaranteed_analysis_data[3], self.element_name_fr)
        self.assertEqual(guaranteed_analysis_data[4], self.element_name_en)
        self.assertEqual(guaranteed_analysis_data[5], self.element_symbol)
        self.assertFalse(guaranteed_analysis_data[6])
        self.assertEqual(
            guaranteed_analysis_data[7],
            (
                self.guaranteed_analysis_name
                + " "
                + str(self.guaranteed_analysis_value)
                + " "
                + self.guaranteed_analysis_unit
            ),
        )

    def test_get_all_guaranteed_analysis(self):
        other_name = "other-nutrient"
        # Create two guaranteed analysis entries
        guaranteed_analysis_id_1 = nutrients.new_guaranteed_analysis(
            self.cursor,
            self.guaranteed_analysis_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        guaranteed_analysis_id_2 = nutrients.new_guaranteed_analysis(
            self.cursor,
            other_name,
            self.guaranteed_analysis_value,
            self.guaranteed_analysis_unit,
            self.label_information_id,
            self.language,
            self.element_id,
            False,
        )
        # Fetch all guaranteed analysis entries
        guaranteed_analysis_data = nutrients.get_all_guaranteeds(
            self.cursor, self.label_information_id
        )
        # Convert the list of tuples into a dictionary where the key is the ID
        guaranteed_analysis_dict = {item[0]: item for item in guaranteed_analysis_data}

        # Assert we have the expected number of entries
        self.assertEqual(len(guaranteed_analysis_dict), 2)

        # Verify the first guaranteed analysis
        self.assertIn(guaranteed_analysis_id_1, guaranteed_analysis_dict)
        guaranteed_analysis_item = guaranteed_analysis_dict[guaranteed_analysis_id_1]
        self.assertEqual(guaranteed_analysis_item[1], self.guaranteed_analysis_name)

        # Verify the second guaranteed analysis
        self.assertIn(guaranteed_analysis_id_2, guaranteed_analysis_dict)
        guaranteed_item = guaranteed_analysis_dict[guaranteed_analysis_id_2]
        self.assertEqual(guaranteed_item[1], other_name)
