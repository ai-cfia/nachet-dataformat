"""
This is a test script for the database packages. 
It tests the functions in the user, seed and picture modules.
"""

import unittest
import uuid
import json
import os
from PIL import Image
import io
import base64
from time import sleep
from unittest.mock import MagicMock

import datastore.db.__init__ as db
from nachet.db.metadata import picture as picture_data
from datastore.db.metadata import picture_set as picture_set_data
from datastore.db.metadata import validator
from datastore.db.queries import picture, user
from nachet.db.queries import inference, machine_learning, seed


NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")


# --------------------  INFERENCE FUNCTIONS --------------------
class test_inference_functions(unittest.TestCase):
    def setUp(self):
        # prepare the connection and cursor
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = db.cursor(self.con)
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

        # prepare the seed
        self.seed_name = "test seed"
        self.seed_id = seed.new_seed(self.cursor, self.seed_name)

        # prepare the user
        self.user_id = user.register_user(self.cursor, "test@email")

        # prepare the picture_set and picture
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.pic_encoded = base64.b64encode(self.image_byte_array.getvalue()).decode(
            "utf8"
        )
        self.picture_set = picture_set_data.build_picture_set_metadata(self.user_id, 1)
        self.nb_seed = 1
        self.picture = picture_data.build_picture(
            self.pic_encoded, "www.link.com", self.nb_seed, 1.0, ""
        )
        self.picture_set_id = picture.new_picture_set(
            self.cursor, self.picture_set, self.user_id
        )
        self.picture_id = picture.new_picture(
            self.cursor, self.picture, self.picture_set_id, self.seed_id, self.nb_seed
        )
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "inference_example.json")
        with open(file_path, "r") as f:
            self.inference = json.loads(f.read())
        self.inference_trim = (
            '{"filename": "inference_example", "totalBoxes": 1, "totalBoxes": 1}'
        )
        self.type = 1
        self.model_id = machine_learning.new_model(self.cursor, "test_model",'test-endpoint',1)
        self.pipeline_id = machine_learning.new_pipeline(self.cursor, json.dumps({}),"test_pipeline",[self.model_id],False)

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_inference(self):
        """
        This test checks if the new_inference function returns a valid UUID
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )

        self.assertTrue(
            validator.is_valid_uuid(inference_id),
            "The inference_id is not a valid UUID",
        )

    def test_new_inference_error(self):
        """
        This test checks if the new_inference function raises an exception when the connection fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(inference.InferenceCreationError):
            inference.new_inference(
                mock_cursor,
                self.inference_trim,
                self.user_id,
                self.picture_id,
                self.type,
                self.pipeline_id
            )

    def test_new_inference_obj(self):
        """
        This test checks if the new_inference_object function returns a valid UUID
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        for box in self.inference["boxes"]:
            inference_obj_id = inference.new_inference_object(
                self.cursor, inference_id, json.dumps(box), self.type
            )
            self.assertTrue(
                validator.is_valid_uuid(inference_obj_id),
                "The inference_obj_id is not a valid UUID",
            )

    def test_new_inference_obj_error(self):
        """
        This test checks if the new_inference_object function raises an exception when the connection fails
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")

        with self.assertRaises(inference.InferenceCreationError):
            inference.new_inference_object(
                mock_cursor, inference_id, self.inference["boxes"][0], self.type
            )

    def test_new_seed_object(self):
        """
        This test checks if the new_seed_object function returns a valid UUID
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        for box in self.inference["boxes"]:
            inference_obj_id = inference.new_inference_object(
                self.cursor, inference_id, json.dumps(box), self.type
            )
            seed_obj_id = inference.new_seed_object(
                self.cursor, self.seed_id, inference_obj_id, box["score"]
            )
            self.assertTrue(
                validator.is_valid_uuid(seed_obj_id),
                "The seed_obj_id is not a valid UUID",
            )

    def test_new_seed_object_error(self):
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(inference.SeedObjectCreationError):
            inference.new_seed_object(mock_cursor, self.seed_id, inference_obj_id, 32.1)

    def test_get_inference(self):
        """
        This test checks if the get_inference function returns a correctly build inference
        TODO : Add test for not existing inference
        """
        inference_trim = json.loads(self.inference_trim)
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_data = inference.get_inference(self.cursor, str(inference_id))
        # inference_json=json.loads(inference_data)
        self.assertGreaterEqual(
            len(inference_trim),
            len(inference_data),
            "The inference is not correctly build and has more keys than expected",
        )
        for key in inference_trim:
            self.assertTrue(
                key in inference_data, f"The key: {key} is not in the inference"
            )
            self.assertEqual(
                inference_trim[key],
                inference_data[key],
                f"The value ({inference_data[key]}) of the key: {key} is not the same as the expected one: {inference_trim[key]}",
            )

    def test_get_inference_object(self):
        """
        This test checks if the get_inference_object function returns a correctly build object
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )

        inference_obj = inference.get_inference_object(
            self.cursor, str(inference_obj_id)
        )

        self.assertEqual(
            len(inference_obj),
            10,
            "The inference object hasn't the number of keys expected",
        )
        self.assertEqual(
            inference_obj[0],
            inference_obj_id,
            "The inference object id is not the same as the expected one",
        )

    def test_get_inference_object_error(self):
        """
        This test checks if the get_inference_object function raise an error if the inference oject does not exist
        """
        inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = "00000000-0000-0000-0000-000000000000"

        with self.assertRaises(Exception):
            inference.get_inference_object(self.cursor, str(inference_obj_id))

    def test_get_objects_by_inference(self):
        """
        This test checks if the get_objects_by_inference function returns the corrects objects for an inference
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        total_boxes = len(self.inference["boxes"])
        objects_id = []
        for box in self.inference["boxes"]:
            inference_obj_id = inference.new_inference_object(
                self.cursor, inference_id, json.dumps(box), self.type
            )
            objects_id.append(inference_obj_id)

        objects = inference.get_objects_by_inference(self.cursor, inference_id)
        self.assertEqual(
            len(objects),
            total_boxes,
            "The number of objects is not the same as the expected one",
        )
        for object in objects:
            self.assertEqual(
                object[2],
                inference_id,
                "The inference id is not the same as the expected one",
            )
            self.assertTrue(
                object[0] in objects_id,
                "The object id is not in the list of expected objects",
            )

    def test_get_inference_object_top_id(self):
        """
        This test checks if the get_inference_object_top_id function returns the correct top_id of an inference object
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        seed_obj_id = inference.new_seed_object(
            self.cursor,
            self.seed_id,
            inference_obj_id,
            self.inference["boxes"][0]["score"],
        )

        inference.set_inference_object_top_id(
            self.cursor, inference_obj_id, seed_obj_id
        )
        top_id = inference.get_inference_object_top_id(self.cursor, inference_obj_id)

        self.assertEqual(
            seed_obj_id, top_id, "The verified_id is not the same as the expected one"
        )

    def test_set_inference_object_verified_id(self):
        """
        This test checks if the set_inference_object_verified_id function returns a correctly update inference object
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        inference.get_inference_object(
            self.cursor, inference_obj_id
        )
        # print(previous_inference_obj)
        seed_obj_id = inference.new_seed_object(
            self.cursor,
            self.seed_id,
            inference_obj_id,
            self.inference["boxes"][0]["score"],
        )
        # Sleep to see a difference in the updated_at date of the object
        sleep(3)

        inference.set_inference_object_verified_id(
            self.cursor, inference_obj_id, seed_obj_id
        )
        inference_obj = inference.get_inference_object(self.cursor, inference_obj_id)
        # print(inference_obj)
        self.assertEqual(
            str(inference_obj[4]),
            str(seed_obj_id),
            "The verified_id is not the same as the expected one",
        )

    def test_set_inference_object_valid(self):
        """
        This test checks if the set_inference_object_verified_id function returns a correctly update inference object
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        inference.get_inference_object(
            self.cursor, inference_obj_id
        )
        # Sleep to see a difference in the updated_at date of the object
        sleep(3)

        inference.set_inference_object_valid(self.cursor, inference_obj_id, True)
        inference_obj = inference.get_inference_object(self.cursor, inference_obj_id)
        self.assertTrue(
            str(inference_obj[5]),
            "The object validity is not the same as the expected one",
        )

        inference.set_inference_object_valid(self.cursor, inference_obj_id, False)
        inference_obj = inference.get_inference_object(self.cursor, inference_obj_id)
        self.assertEqual(
            str(inference_obj[6]),
            "False",
            "The object validity is not the same as the expected one",
        )

    def test_is_inference_verified(self):
        """
        Test if is_inference_verified function correctly returns the inference status
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )

        verified = inference.is_inference_verified(self.cursor, inference_id)
        self.assertFalse(verified, "The inference verified field should be False")

        inference.set_inference_verified(self.cursor, inference_id, True)

        verified = inference.is_inference_verified(self.cursor, inference_id)
        self.assertTrue(verified, "The inference should be fully verified")

    def test_verify_inference_status(self):
        """
        Test if verify_inference_status function correctly updates the inference status
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        seed_obj_id = inference.new_seed_object(
            self.cursor,
            self.seed_id,
            inference_obj_id,
            self.inference["boxes"][0]["score"],
        )

        inference.verify_inference_status(self.cursor, inference_id, self.user_id)

        verified = inference.is_inference_verified(self.cursor, inference_id)
        self.assertFalse(verified, "The inference verified field should be False")

        inference.set_inference_object_valid(self.cursor, inference_obj_id, True)
        inference.set_inference_object_verified_id(
            self.cursor, inference_obj_id, seed_obj_id
        )

        inference.verify_inference_status(self.cursor, inference_id, self.user_id)
        verified = inference.is_inference_verified(self.cursor, inference_id)
        self.assertTrue(verified, "The inference should be fully verified")

    def test_get_seed_object_id(self):
        """
        Test if get_seed_object_id function correctly returns the seed object id
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        seed_obj_id = inference.new_seed_object(
            self.cursor,
            self.seed_id,
            inference_obj_id,
            self.inference["boxes"][0]["score"],
        )

        fetched_seed_obj_id = inference.get_seed_object_id(
            self.cursor, self.seed_id, inference_obj_id
        )
        self.assertEqual(
            seed_obj_id,
            fetched_seed_obj_id,
            "The fetched seed object id is not the same as the expected one",
        )

    def test_get_not_seed_object_id(self):
        """
        Test if get_seed_object_id function correctly returns the seed object id
        """
        inference_id = inference.new_inference(
            self.cursor, self.inference_trim, self.user_id, self.picture_id, self.type, self.pipeline_id
        )
        inference_obj_id = inference.new_inference_object(
            self.cursor, inference_id, json.dumps(self.inference["boxes"][0]), self.type
        )
        inference.new_seed_object(
            self.cursor,
            self.seed_id,
            inference_obj_id,
            self.inference["boxes"][0]["score"],
        )
        mock_seed_id = str(uuid.uuid4())
        fetched_seed_obj_id = inference.get_seed_object_id(
            self.cursor, mock_seed_id, inference_obj_id
        )
        self.assertTrue(
            fetched_seed_obj_id is None, "The fetched seed object id should be None"
        )
