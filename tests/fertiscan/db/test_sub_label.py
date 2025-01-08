"""
This is a test script for the database packages.
It tests the functions in the user, seed and picture modules.
"""

import os
import unittest
import uuid

import datastore.db as db
from datastore.db.metadata import validator
from fertiscan.db.queries import label, sub_label

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class test_sub_type(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        self.type_fr = "text_fr"
        self.type_en = "text_en"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_sub_type(self):
        sub_type_id = sub_label.new_sub_type(self.cursor, self.type_fr, self.type_en)
        self.assertTrue(validator.is_valid_uuid(sub_type_id))

    def test_new_sub_type_duplicate(self):
        sub_label.new_sub_type(self.cursor, self.type_fr, self.type_en)
        with self.assertRaises(sub_label.SubTypeCreationError):
            sub_label.new_sub_type(self.cursor, self.type_fr, self.type_en)

    def test_get_sub_type_id(self):
        sub_type_id = sub_label.new_sub_type(self.cursor, self.type_fr, self.type_en)
        data_en = sub_label.get_sub_type_id(self.cursor, self.type_en)
        data_fr = sub_label.get_sub_type_id(self.cursor, self.type_fr)
        self.assertEqual(str(data_en), str(sub_type_id))
        self.assertEqual(str(data_fr), str(sub_type_id))

    def test_get_sub_type_id_not_found(self):
        with self.assertRaises(sub_label.SubTypeQueryError):
            sub_label.get_sub_type_id(self.cursor, "not-a-type")


class test_sub_label(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

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
        self.language = "fr"

        self.type_fr = "test-type-fr"
        self.type_en = "test-type-en"
        self.type_2_fr = "test-type-2-fr"
        self.type_2_en = "test-type-2-en"
        self.sub_type_id = sub_label.new_sub_type(
            self.cursor, self.type_fr, self.type_en
        )
        self.sub_type_2_id = sub_label.new_sub_type(
            self.cursor, self.type_2_fr, self.type_2_en
        )
        self.text_fr = "text_fr"
        self.text_en = "text_en"
        self.text_fr_2 = "text_fr_2"
        self.text_en_2 = "text_en_2"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_sub_label(self):
        sub_label_id = sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        self.assertTrue(validator.is_valid_uuid(sub_label_id))

    def test_get_sub_label(self):
        sub_label_id = sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        sub_label_data = sub_label.get_sub_label(self.cursor, sub_label_id)
        self.assertEqual(sub_label_data[0], self.text_fr)
        self.assertEqual(sub_label_data[1], self.text_en)

    def test_get_sub_label_json(self):
        sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        sub_label.new_sub_label(
            self.cursor,
            self.text_fr_2,
            self.text_en_2,
            self.label_id,
            self.sub_type_2_id,
            False,
        )
        sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        sub_label_data = sub_label.get_sub_label_json(self.cursor, self.label_id)
        self.assertTrue(self.type_en in sub_label_data.keys())

    def test_get_sub_label_not_found(self):
        data = sub_label.get_sub_label_json(self.cursor, str(uuid.uuid4()))
        for key in data.keys():
            for item in data[key]:
                self.assertEqual(data[key][item], [])

    def test_has_sub_label(self):
        sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        self.assertTrue(sub_label.has_sub_label(self.cursor, self.label_id))

    def test_has_sub_label_not_found(self):
        self.assertFalse(sub_label.has_sub_label(self.cursor, str(uuid.uuid4())))

    def test_get_full_sub_label(self):
        sub_label_id = sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        sub_label_data = sub_label.get_full_sub_label(self.cursor, sub_label_id)
        self.assertEqual(sub_label_data[0], sub_label_id)
        self.assertEqual(sub_label_data[1], self.text_fr)
        self.assertEqual(sub_label_data[2], self.text_en)
        self.assertEqual(sub_label_data[4], self.type_fr)
        self.assertEqual(sub_label_data[5], self.type_en)

    def test_get_all_sub_label(self):
        other_fr = "other_fr"
        other_en = "other_en"

        sub_label_id_1 = sub_label.new_sub_label(
            self.cursor,
            self.text_fr,
            self.text_en,
            self.label_id,
            self.sub_type_id,
            False,
        )
        sub_label_id_2 = sub_label.new_sub_label(
            self.cursor, other_fr, other_en, self.label_id, self.sub_type_id, False
        )

        # Fetch all sub_labels
        sub_label_data = sub_label.get_all_sub_label(self.cursor, self.label_id)

        # Assert the length of results is 2
        self.assertEqual(len(sub_label_data), 2)

        # Extract the IDs and their corresponding data from the returned result set
        result_dict = {row[0]: row for row in sub_label_data}

        # Verify that both IDs exist in the returned results
        self.assertIn(sub_label_id_1, result_dict)
        self.assertIn(sub_label_id_2, result_dict)

        # Check that the data for sub_label_id_1 matches the expected values
        self.assertEqual(result_dict[sub_label_id_1][1], self.text_fr)
        self.assertEqual(result_dict[sub_label_id_1][2], self.text_en)

        # Check that the data for sub_label_id_2 matches the expected values
        self.assertEqual(result_dict[sub_label_id_2][1], other_fr)
        self.assertEqual(result_dict[sub_label_id_2][2], other_en)

        # Ensure both sub_label_id_1 and sub_label_id_2 are valid UUIDs
        self.assertTrue(validator.is_valid_uuid(sub_label_id_1))
        self.assertTrue(validator.is_valid_uuid(sub_label_id_2))

    def test_get_sub_label_json_with_null_values(self):
        # Insert a sub-label with NULL for text_fr
        sub_label.new_sub_label(
            self.cursor,
            None,  # Null French text
            self.text_en,  # English text
            self.label_id,
            self.sub_type_id,
            False,
        )

        # Insert a sub-label with NULL for text_en
        sub_label.new_sub_label(
            self.cursor,
            self.text_fr,  # French text
            None,  # Null English text
            self.label_id,
            self.sub_type_2_id,
            False,
        )

        # Fetch sub-label data as JSON
        sub_label_data = sub_label.get_sub_label_json(self.cursor, self.label_id)

        # Get the result dict to map sub-type to sub-label data
        result_dict = {
            sub_type: sub_label_data[sub_type] for sub_type in sub_label_data
        }

        # Check that the 'en' array for the first sub-label (sub_type_id) contains the correct English text
        self.assertIn(self.type_en, result_dict)
        self.assertEqual(
            result_dict[self.type_en]["en"],
            [self.text_en],
            "Expected 'en' array to contain the correct English text for sub_type_id",
        )

        # Check that the 'fr' array for the first sub-label (sub_type_id) contains an empty string
        self.assertEqual(
            result_dict[self.type_en]["fr"],
            [""],  # Since None should be replaced by an empty string
            "Expected 'fr' array to contain an empty string for sub_type_id since it was NULL",
        )

        # Check that the 'fr' array for the second sub-label (sub_type_2_id) contains the correct French text
        self.assertIn(self.type_2_en, result_dict)
        self.assertEqual(
            result_dict[self.type_2_en]["fr"],
            [self.text_fr],
            "Expected 'fr' array to contain the correct French text for sub_type_2_id",
        )

        # Check that the 'en' array for the second sub-label (sub_type_2_id) contains an empty string
        self.assertEqual(
            result_dict[self.type_2_en]["en"],
            [""],  # Since None should be replaced by an empty string
            "Expected 'en' array to contain an empty string for sub_type_2_id since it was NULL",
        )

    def test_sub_label_insertion_raises_exception_for_null_or_empty_texts(self):
        # Test that an exception is raised when both 'text_content_fr' and 'text_content_en' are None or empty

        # Attempt to insert a sub-label with both English and French texts as NULL
        with self.assertRaises(Exception):
            sub_label.new_sub_label(
                self.cursor,
                None,  # Null French text
                None,  # Null English text
                self.label_id,
                self.sub_type_id,
                False,
            )

        # Attempt to insert a sub-label with both English and French texts as empty strings
        with self.assertRaises(Exception):
            sub_label.new_sub_label(
                self.cursor,
                "",  # Empty French text
                "",  # Empty English text
                self.label_id,
                self.sub_type_id,
                False,
            )
