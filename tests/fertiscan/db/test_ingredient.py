"""
This is a test script for the database packages.
It tests the functions in the ingredient module.
"""

import os
import unittest

import datastore.db as db
from datastore.db.metadata import validator
from fertiscan.db.queries import ingredient, label

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")


class test_ingredient(unittest.TestCase):
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

        self.ingredient_name = "ingredient_name"
        self.value = 10.0
        self.unit = "unit"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_ingredient(self):
        ingredient_id = ingredient.new_ingredient(
            self.cursor,
            self.ingredient_name,
            self.value,
            self.unit,
            self.label_id,
            self.language,
            False,
            False,
            False,
        )
        self.assertTrue(validator.is_valid_uuid(ingredient_id))

    def test_new_ingredient_empty(self):
        with self.assertRaises(ingredient.IngredientCreationError):
            ingredient.new_ingredient(
                self.cursor,
                None,
                None,
                None,
                None,
                self.language,
                False,
                False,
                False,
            )

    def test_get_ingredient_json(self):
        nom = "nom_ingredient"
        name = "ingredient_name"
        ingredient.new_ingredient(
            self.cursor,
            nom,
            self.value,
            self.unit,
            self.label_id,
            "fr",
            False,
            False,
            False,
        )
        ingredient.new_ingredient(
            self.cursor,
            name,
            self.value,
            self.unit,
            self.label_id,
            "en",
            False,
            False,
            False,
        )

        ingredient_obj = ingredient.get_ingredient_json(self.cursor, self.label_id)
        self.assertIsNotNone(ingredient_obj["ingredients"]["en"])
        self.assertEqual(len(ingredient_obj.get("ingredients").get("en")), 1)
        self.assertEqual(len(ingredient_obj["ingredients"]["fr"]), 1)

    def test_get_ingredient_json_empty(self):
        ingredient_obj = ingredient.get_ingredient_json(self.cursor, self.label_id)
        self.assertIsNotNone(ingredient_obj.get("ingredients").get("en"))
        self.assertIsNotNone(ingredient_obj.get("ingredients").get("fr"))
        self.assertEqual(len(ingredient_obj.get("ingredients").get("en")), 0)
        self.assertEqual(len(ingredient_obj.get("ingredients").get("fr")), 0)

    def test_get_ingredient_json_record_keeping(self):
        label_id_record_keeping = label.new_label_information(
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
            True,
        )

        ingredient.new_ingredient(
            self.cursor,
            self.ingredient_name,
            self.value,
            self.unit,
            label_id_record_keeping,
            self.language,
            False,
            False,
            False,
        )

        ingredient.new_ingredient(
            self.cursor,
            self.ingredient_name,
            self.value,
            self.unit,
            self.label_id,
            self.language,
            False,
            False,
            False,
        )

        ingredient_obj = ingredient.get_ingredient_json(
            self.cursor, self.label_id
        )
        ingredient_empty = ingredient.get_ingredient_json(
            self.cursor, label_id_record_keeping
        )
        # check that the upload worked on not record keeping label
        self.assertEqual(len(ingredient_obj.get("ingredients").get("fr")),1)
        # make sure that the record keeping label does not display any ingredients
        self.assertEqual(len(ingredient_empty.get("ingredients").get("fr")),0)
