"""
This is a test script for the highest level of the datastore packages.
It tests the functions in the __init__.py files of the datastore packages.
"""

import asyncio
import io
import json
import os
import unittest

from PIL import Image

import datastore
import datastore.db as db
import datastore.db.metadata.validator as validator
import fertiscan
import fertiscan.db.metadata.inspection as metadata
from datastore.db.queries import picture
from fertiscan.db.queries import (
    inspection,
    label,
    metric,
    nutrients,
    sub_label,
    ingredient,
    organization,
)

BLOB_CONNECTION_STRING = os.environ["FERTISCAN_STORAGE_URL"]
if BLOB_CONNECTION_STRING is None or BLOB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_STORAGE_URL_TESTING is not set")

DB_CONNECTION_STRING = os.environ.get("FERTISCAN_DB_URL")
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("FERTISCAN_DB_URL is not set")

DB_SCHEMA = os.environ.get("FERTISCAN_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("FERTISCAN_SCHEMA_TESTING is not set")

BLOB_ACCOUNT = os.environ["FERTISCAN_BLOB_ACCOUNT"]
if BLOB_ACCOUNT is None or BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

BLOB_KEY = os.environ["FERTISCAN_BLOB_KEY"]
if BLOB_KEY is None or BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")

TEST_INSPECTION_JSON_PATH = "tests/fertiscan/inspection.json"


def loop_into_empty_dict(dict_data):
    passing = True
    for key, value in dict_data.items():
        if isinstance(value, dict):
            loop_into_empty_dict(value)
        elif isinstance(value, list):
            if len(value) == 0:
                continue
            else:
                passing = False
        elif isinstance(value, bool):
            if not value:
                continue
            else:
                passing = False
        else:
            if value is None:
                continue
            elif validator.is_valid_uuid(value):
                continue
            else:
                passing = False
    return passing


class TestDatastore(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "analyse.json")
        with open(file_path, "r") as file:
            self.analysis_json = json.load(file)
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.user_email = "testesss@email"
        self.tier = "test-user"
        self.user = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, BLOB_CONNECTION_STRING, self.tier
            )
        )
        self.container_client = asyncio.run(
            datastore.get_user_container_client(
                self.user.id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                self.tier,
            )
        )

        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.pic_encoded = self.image.tobytes()

        if len(self.analysis_json.get("cautions_en")) >= len(
            self.analysis_json.get("cautions_fr")
        ):
            self.nb_cautions = len(self.analysis_json.get("cautions_en"))
        elif len(self.analysis_json.get("cautions_en")) < len(
            self.analysis_json.get("cautions_fr")
        ):
            self.nb_cautions = len(self.analysis_json.get("cautions_fr"))

        if len(self.analysis_json.get("instructions_en")) >= len(
            self.analysis_json.get("instructions_fr")
        ):
            self.nb_instructions = len(self.analysis_json.get("instructions_en"))
        elif len(self.analysis_json.get("instructions_en")) < len(
            self.analysis_json.get("instructions_fr")
        ):
            self.nb_instructions = len(self.analysis_json.get("instructions_fr"))

        # if len(self.analysis_json.get("first_aid_en")) >= len(
        # self.analysis_json.get("first_aid_fr")
        # ):
        # self.nb_first_aid = len(self.analysis_json.get("first_aid_en"))
        # elif len(self.analysis_json.get("first_aid_en")) < len(
        # self.analysis_json.get("first_aid_fr")
        # ):
        # self.nb_first_aid = len(self.analysis_json.get("first_aid_fr"))

        # self.nb_specifications = len(self.analysis_json.get("specifications_en")) + len(
        # self.analysis_json.get("specifications_fr")
        # )

        self.nb_guaranteed = len(
            self.analysis_json.get("guaranteed_analysis_en").get("nutrients")
        ) + len(self.analysis_json.get("guaranteed_analysis_fr").get("nutrients"))

        self.nb_ingredients = len(self.analysis_json.get("ingredients_en")) + len(
            self.analysis_json.get("ingredients_fr")
        )

        # self.nb_micronutrients = len(self.analysis_json.get("micronutrients_en")) + len(
        # self.analysis_json.get("micronutrients_fr")
        # )

        self.nb_weight = len(self.analysis_json.get("weight"))

    def tearDown(self):
        try:
            self.con.rollback()
            db.end_query(self.con, self.cursor)
            self.container_client.delete_container()
        except Exception as e:
            print(e)

    def test_register_analysis(self):
        # print(self.user.id)
        self.assertTrue(self.container_client.exists())
        analysis = asyncio.run(
            fertiscan.register_analysis(
                self.cursor,
                self.container_client,
                self.user.id,
                [self.pic_encoded, self.pic_encoded],
                self.analysis_json,
            )
        )
        self.assertIsNotNone(analysis)
        self.assertTrue(validator.is_valid_uuid(analysis["inspection_id"]))
        inspection_id = analysis["inspection_id"]

        self.assertTrue(validator.is_valid_uuid(analysis["product"]["label_id"]))
        label_id = analysis["product"]["label_id"]

        metrics = metric.get_metric_by_label(
            self.cursor, str(analysis["product"]["label_id"])
        )

        self.assertIsNotNone(metrics)
        self.assertEqual(
            len(metrics), 4
        )  # There are 4 metrics in the analysis_json (1 volume, 1 density, 2 weight )

        ingredients = ingredient.get_ingredient_json(
            self.cursor, str(analysis["product"]["label_id"])
        )
        self.assertIsNotNone(ingredients)
        # print(ingredients)

        # specifications = specification.get_all_specifications(
        # cursor=self.cursor, label_id=str(analysis["product"]["label_id"])
        # )
        # self.assertIsNotNone(specifications)
        # self.assertEqual(
        # len(specifications), self.nb_specifications
        # )  # There are 2 specifications in the analysis_json

        # nutrients_data = nutrients.get_all_micronutrients(
        # cursor=self.cursor, label_id=str(analysis["product"]["label_id"])
        # )
        # self.assertIsNotNone(nutrients_data)

        # self.assertEqual(
        # len(nutrients_data), self.nb_micronutrients
        # )  # There are 2 nutrients in the analysis_json
        sub_labels = sub_label.get_sub_label_json(
            self.cursor, str(analysis["product"]["label_id"])
        )
        self.assertIsNotNone(sub_labels)

        # Test for original_dataset
        inspection.get_inspection(self.cursor, inspection_id)

        # original_dataset = inspection_data[8]
        # original_dataset["inspection_id"] = inspection_id
        self.maxDiff = None
        # self.assertDictEqual(analysis, original_dataset)

        # Verify OLAP Layer

        query = "SELECT EXISTS (SELECT 1 FROM inspection_factual WHERE inspection_factual.inspection_id = %s)"

        self.cursor.execute(query, (inspection_id,))
        self.assertTrue(self.cursor.fetchone()[0])

        query = "SELECT EXISTS (SELECT 1 FROM label_dimension WHERE label_dimension.label_id = %s)"

        self.cursor.execute(query, (label_id,))
        self.assertTrue(self.cursor.fetchone()[0])

        # Verify if the saved ids are the same length as the ones in the analysis_json

        label_dimension = label.get_label_dimension(self.cursor, label_id)

        self.assertEqual(
            str(label_dimension[1][0]), str(analysis["organizations"][0]["id"])
        )
        self.assertEqual(
            str(label_dimension[1][1]), str(analysis["organizations"][1]["id"])
        )

        self.assertEqual(len(label_dimension[2]), self.nb_instructions)

        self.assertEqual(len(label_dimension[3]), self.nb_cautions)
        # self.assertEqual(len(label_dimension[7]), self.nb_first_aid)

        # self.assertEqual(len(label_dimension[6]), self.nb_specifications)
        self.assertEqual(len(label_dimension[7]), self.nb_ingredients)
        # self.assertEqual(len(label_dimension[8]), self.nb_micronutrients)
        self.assertEqual(len(label_dimension[9]), self.nb_guaranteed)
        self.assertEqual(len(label_dimension[10]), self.nb_weight)
        self.assertEqual(len(label_dimension[11]), 1)
        self.assertEqual(len(label_dimension[12]), 1)

    def test_register_analysis_empty(self):
        empty_analysis = {
            "organizations": [],
            "fertiliser_name": None,
            "registration_number": [],
            "lot_number": None,
            "weight": [],
            "density": None,
            "volume": None,
            "npk": None,
            "cautions_en": [],
            "instructions_en": [],
            "cautions_fr": [],
            "instructions_fr": [],
            "guaranteed_analysis_is_minimal": False,
            "guaranteed_analysis_en": {"title": None, "nutrients": []},
            "guaranteed_analysis_fr": {"title": None, "nutrients": []},
        }

        formatted_analysis = metadata.build_inspection_import(
            empty_analysis, self.user.id
        )
        picture_set_id = picture.new_picture_set(
            self.cursor, json.dumps({}), self.user.id
        )

        inspection_dict = inspection.new_inspection_with_label_info(
            self.cursor, self.user.id, picture_set_id, formatted_analysis
        )
        inspection_id = inspection_dict["inspection_id"]
        label_id = inspection_dict["product"]["label_id"]
        self.assertTrue(validator.is_valid_uuid(inspection_id))

        # Verify the data
        label_data = label.get_label_information(self.cursor, label_id)
        self.assertIsNotNone(label_data)
        self.assertIsNone(label_data[1])

        # Verify getters
        inspection_data = metadata.build_inspection_export(self.cursor, inspection_id)
        inspection_data = json.loads(inspection_data)
        # TODO: investigate if this should pass and why it doesn't
        # Make sure the inspection data is either a empty array or None
        # self.assertTrue(loop_into_empty_dict(inspection_data))

    def test_register_analysis_invalid_user(self):
        with self.assertRaises(Exception):
            asyncio.run(
                fertiscan.register_analysis(
                    self.cursor,
                    self.container_client,
                    "invalid_user_id",
                    [self.pic_encoded, self.pic_encoded],
                    self.analysis_json,
                )
            )

    def test_register_analysy_missing_key(self):
        self.analysis_json.pop("specification_en", None)
        with self.assertRaises(fertiscan.data_inspection.BuildInspectionImportError):
            asyncio.run(
                fertiscan.register_analysis(
                    self.cursor,
                    self.container_client,
                    self.user.id,
                    [self.pic_encoded, self.pic_encoded],
                    {},
                )
            )

    def test_get_full_inspection_json(self):
        formatted_analysis = metadata.build_inspection_import(
            self.analysis_json, self.user.id
        )
        picture_set_id = picture.new_picture_set(
            self.cursor, json.dumps({}), self.user.id
        )

        inspection_dict = inspection.new_inspection_with_label_info(
            self.cursor, self.user.id, picture_set_id, formatted_analysis
        )
        inspection_id = inspection_dict["inspection_id"]

        data = asyncio.run(
            fertiscan.get_full_inspection_json(self.cursor, inspection_id)
        )
        data = json.loads(data)
        self.assertEqual(data["inspection_id"], str(inspection_id))
        self.assertEqual(data["inspector_id"], str(self.user.id))

    def test_delete_inspection(self):
        # Create a new inspection to delete later
        with open(TEST_INSPECTION_JSON_PATH, "r") as file:
            input_json = json.load(file)

        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user.id
            )
        )

        inspection_dict = inspection.new_inspection_with_label_info(
            self.cursor, self.user.id, picture_set_id, json.dumps(input_json)
        )
        inspection_id = inspection_dict["inspection_id"]

        # Verify the inspection was created by directly querying the database
        self.cursor.execute(
            "SELECT id FROM inspection WHERE id = %s;",
            (inspection_id,),
        )
        fetched_inspection_id = self.cursor.fetchone()
        self.assertIsNotNone(
            fetched_inspection_id, "The inspection should exist before deletion."
        )

        # Perform the delete operation
        deleted_inspection = asyncio.run(
            fertiscan.delete_inspection(
                self.cursor, inspection_id, self.user.id, self.container_client
            )
        )

        # Verify that the inspection ID matches the one we deleted
        self.assertIsInstance(deleted_inspection, metadata.DBInspection)
        self.assertEqual(str(deleted_inspection.id), inspection_id)

        # Ensure that the inspection no longer exists in the database
        self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM inspection WHERE id = %s);",
            (inspection_id,),
        )
        inspection_exists = self.cursor.fetchone()[0]
        self.assertFalse(
            inspection_exists, "The inspection should be deleted from the database."
        )

        # Verify that the picture set associated with the inspection was also deleted
        self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM picture_set WHERE id = %s);",
            (picture_set_id,),
        )
        picture_set_exists = self.cursor.fetchone()[0]
        self.assertFalse(
            picture_set_exists,
            "The picture set should be deleted from the database.",
        )

        # Verify that no blobs associated with the picture set ID remain in the container
        blobs_after = [blob.name for blob in self.container_client.list_blobs()]
        self.assertFalse(
            any(str(picture_set_id) in blob_name for blob_name in blobs_after),
            "The folder associated with the picture set ID should be deleted from the container.",
        )

    def test_update_inspection(self):
        self.assertTrue(self.container_client.exists())
        analysis = asyncio.run(
            fertiscan.register_analysis(
                self.cursor,
                self.container_client,
                self.user.id,
                [self.pic_encoded, self.pic_encoded],
                self.analysis_json,
            )
        )
        self.assertIsNotNone(analysis)
        inspection_id = analysis["inspection_id"]
        label_id = analysis["product"]["label_id"]
        self.assertTrue(validator.is_valid_uuid(inspection_id))
        # new values
        new_product_name = "New Product Name"
        untouched_weight = analysis["product"]["metrics"]["weight"][1]["value"]
        new_weight = 1000.0
        untouched_volume = analysis["product"]["metrics"]["volume"]["value"]
        new_density = 10.0
        old_npk = analysis["product"]["npk"]
        new_npk = "10-10-10"
        new_instruction_en = ["3. of", "2. set"]
        new_instruction_fr = ["3. de", "2. ensemble"]
        new_instruction_nb = (len(new_instruction_en) + len(new_instruction_fr)) / 2
        new_value = 100.0
        old_value = analysis["guaranteed_analysis"]["fr"][0]["value"]
        new_title = "Nouveau titre"
        old_title = analysis["guaranteed_analysis"]["title"]["fr"]
        old_name = analysis["guaranteed_analysis"]["fr"][0]["name"]
        new_name = "Nouveau nom"
        user_feedback = "This is a feedback"
        new_record_keeping = True
        # new_specification_en = [
        #     {"humidity": new_value, "ph": 6.5, "solubility": 100, "edited": True}
        # ]
        new_cautions_en = [
            "In case of contact with eyes, rinse immediately with plenty of water and seek medical advice.",
            "NEWLY ADDED FIRST AID",
            "test",
            "test",
            "test",
        ]
        new_cautions_fr = [
            "En cas de contact avec les yeux, rincer immédiatement à l'eau et consulter un médecin.",
            "NOUVELLE PREMIÈRE AIDE AJOUTÉE",
            "test",
            "test",
            "test",
        ]
        new_caution_number = (len(new_cautions_en) + len(new_cautions_fr)) / 2
        new_guaranteed_analysis = {
            "title": {"en": new_title, "fr": old_title},
            "is_minimal": False,
            "en": [
                {
                    "value": new_value,
                    "unit": "%",
                    "name": new_name,
                    "edited": True,
                },
            ],
            "fr": [
                {
                    "value": old_value,
                    "unit": "%",
                    "name": old_name,
                    "edited": False,
                },
            ],
        }

        new_guaranteed_nb = 2

        old_organizations = analysis["organizations"]
        new_organizations = [
            {
                "name": "New Organization",
                "address": "New Address",
                "phone": "New Phone",
                "email": "New Email",
                "website": "New Website",
            }
        ]
        # update the dataset
        analysis["product"]["name"] = new_product_name
        analysis["product"]["metrics"]["weight"][0]["value"] = new_weight
        analysis["product"]["metrics"]["weight"][0]["edited"] = True
        analysis["product"]["metrics"]["density"]["value"] = new_density
        analysis["product"]["metrics"]["density"]["edited"] = True
        analysis["product"]["record_keeping"] = new_record_keeping
        analysis["product"]["npk"] = new_npk
        analysis["instructions"]["en"] = new_instruction_en
        analysis["instructions"]["fr"] = new_instruction_fr
        # analysis["specifications"]["en"] = new_specification_en
        analysis["cautions"]["en"] = new_cautions_en
        analysis["cautions"]["fr"] = new_cautions_fr
        analysis["guaranteed_analysis"] = new_guaranteed_analysis
        analysis["organizations"] = new_organizations
        analysis["inspection_comment"] = user_feedback

        old_label_dimension = label.get_label_dimension(self.cursor, label_id)

        asyncio.run(
            fertiscan.update_inspection(
                self.cursor, inspection_id, self.user.id, analysis
            )
        )

        # check if specifications are updated
        # specifications = specification.get_all_specifications(self.cursor, label_id)
        # for specific in specifications:
        #     if specific[5] == "en":
        #         self.assertTrue(specific[4])
        #         self.assertEqual(specific[1], new_value)
        #     else:
        #         self.assertFalse(specific[4])
        #         self.assertEqual(specific[1], old_value)
        # check if metrics are updated correctly
        metrics = metric.get_metric_by_label(self.cursor, label_id)
        for metric_data in metrics:
            if metric_data[4] == "weight":
                if metric_data[3] is True:
                    self.assertEqual(metric_data[1], new_weight)
                else:
                    self.assertEqual(metric_data[1], untouched_weight)
            elif metric_data[4] == "density":
                self.assertEqual(metric_data[1], new_density)
                self.assertTrue(metric_data[3])
            elif metric_data[4] == "volume":
                self.assertEqual(metric_data[1], untouched_volume)
                self.assertFalse(metric_data[3])
        # verify npk update & guaranteed title updates(label_information)
        label_info_data = label.get_label_information(self.cursor, label_id)
        self.assertEqual(label_info_data[3], new_npk)
        self.assertNotEqual(label_info_data[3], old_npk)
        self.assertEqual(label_info_data[7], new_title)
        self.assertNotEqual(label_info_data[7], old_title)
        self.assertEqual(label_info_data[8], old_title)
        self.assertEqual(label_info_data[10], new_record_keeping)

        guaranteed_data = nutrients.get_all_guaranteeds(self.cursor, label_id)
        for guaranteed in guaranteed_data:
            if guaranteed[7]:
                self.assertEqual(guaranteed[1], new_value)
            else:
                self.assertEqual(guaranteed[1], old_value)

        # Verify user's comment are saved
        inspection_data = inspection.get_inspection(self.cursor, inspection_id)
        self.assertEqual(inspection_data[8], user_feedback)

        # Verify organizations are saved
        orgs = organization.get_organizations_info_label(self.cursor, label_id)

        self.assertEqual(len(orgs), 3)  # 2 default + 1 new
        self.assertEqual(len(orgs), len(old_organizations) + 1)

        # VERIFY OLAP
        new_label_dimension = label.get_label_dimension(self.cursor, label_id)

        # Check if sub_label created a new id if there is a field that is not in the old label_dimension
        self.assertEqual(len(old_label_dimension[3]), self.nb_cautions)

        self.assertEqual(len(new_label_dimension[3]), new_caution_number)
        self.assertNotEqual(len(new_label_dimension[3]), len(old_label_dimension[6]))
        # Check if the total of sub_label reduced after a field has been removed
        self.assertEqual(len(old_label_dimension[2]), self.nb_instructions)
        self.assertEqual(len(new_label_dimension[2]), new_instruction_nb)
        self.assertNotEqual(len(new_label_dimension[2]), len(old_label_dimension[5]))
        # Check if the total of guaranteed is reduced after a field has been removed
        self.assertEqual(len(old_label_dimension[9]), self.nb_guaranteed)
        self.assertEqual(len(new_label_dimension[9]), new_guaranteed_nb)
        self.assertNotEqual(len(new_label_dimension[9]), len(old_label_dimension[12]))

        new_guaranteed_analysis = {
            "title": {"en": new_title, "fr": old_title},
            "is_minimal": False,
            "en": [
                {
                    "value": new_value,
                    "unit": "%",
                    "name": new_name,
                    "edited": True,
                },
                {
                    "value": new_value,
                    "unit": "%",
                    "name": new_name,
                    "edited": True,
                },
                {
                    "value": new_value,
                    "unit": "%",
                    "name": new_name,
                    "edited": True,
                },
                {
                    "value": new_value,
                    "unit": "%",
                    "name": new_name,
                    "edited": True,
                },
            ],
            "fr": [
                {
                    "value": old_value,
                    "unit": "%",
                    "name": old_name,
                    "edited": False,
                },
                {
                    "value": old_value,
                    "unit": "%",
                    "name": old_name,
                    "edited": False,
                },
                {
                    "value": old_value,
                    "unit": "%",
                    "name": old_name,
                    "edited": False,
                },
                {
                    "value": old_value,
                    "unit": "%",
                    "name": old_name,
                    "edited": False,
                },
            ],
        }
        old_guaranteed_nb = new_guaranteed_nb
        new_guaranteed_nb = 8
        analysis["guaranteed_analysis"] = new_guaranteed_analysis
        asyncio.run(
            fertiscan.update_inspection(
                self.cursor, inspection_id, self.user.id, analysis
            )
        )

        new_label_dimension = label.get_label_dimension(self.cursor, label_id)

        # Check if the total of guaranteed is increased after a field has been added
        self.assertEqual(len(new_label_dimension[9]), new_guaranteed_nb)
        self.assertNotEqual(len(new_label_dimension[9]), len(old_label_dimension[12]))
        self.assertNotEqual(len(new_label_dimension[9]), old_guaranteed_nb)
