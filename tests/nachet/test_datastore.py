"""
This is a test script for the highest level of the datastore packages. 
It tests the functions in the __init__.py files of the datastore packages.
"""

import io
import os
import unittest
from unittest.mock import MagicMock
from PIL import Image, ImageChops
import json
import uuid
import asyncio
import datastore.db.__init__ as db
import datastore.__init__ as datastore
import nachet.__init__ as nachet
import datastore.db.metadata.validator as validator
import nachet.db.queries.seed as seed_query
from copy import deepcopy


NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")

BLOB_CONNECTION_STRING = os.environ["NACHET_STORAGE_URL"]
if BLOB_CONNECTION_STRING is None or BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL_TESTING is not set")

BLOB_ACCOUNT = os.environ["NACHET_BLOB_ACCOUNT"]
if BLOB_ACCOUNT is None or BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

BLOB_KEY = os.environ["NACHET_BLOB_KEY"]
if BLOB_KEY is None or BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")

DEV_USER_EMAIL = os.environ.get("DEV_USER_EMAIL")
if DEV_USER_EMAIL is None or DEV_USER_EMAIL == "":
    # raise ValueError("DEV_USER_EMAIL is not set")
    print("Warning: DEV_USER_EMAIL not set")


class test_ml_structure(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "ml_structure_exemple.json")
        with open(file_path) as file:
            self.ml_dict = json.load(file)
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_import_ml_structure_from_json(self):
        """
        Test the import function.
        """
        asyncio.run(
            nachet.import_ml_structure_from_json_version(self.cursor, self.ml_dict)
        )
        self.cursor.execute("SELECT id FROM model WHERE name='that_model_name'")
        model_id = self.cursor.fetchone()[0]
        self.assertTrue(validator.is_valid_uuid(str(model_id)))
        self.cursor.execute("SELECT id FROM pipeline WHERE name='Second Pipeline'")
        pipeline_id = self.cursor.fetchone()[0]
        self.assertTrue(validator.is_valid_uuid(str(pipeline_id)))
        self.cursor.execute(
            "SELECT id FROM pipeline_model WHERE pipeline_id=%s AND model_id=%s",
            (
                pipeline_id,
                model_id,
            ),
        )
        self.assertTrue(validator.is_valid_uuid(self.cursor.fetchone()[0]))

    def test_get_ml_structure(self):
        """
        Test the get function.
        """

        # asyncio.run(datastore.import_ml_structure_from_json_version(self.cursor,self.ml_dict))
        ml_structure = asyncio.run(nachet.get_ml_structure(self.cursor))
        # self.assertDictEqual(ml_structure,self.ml_dict)
        for pipeline in self.ml_dict["pipelines"]:
            for key in pipeline:
                if key != "Accuracy":
                    self.assertTrue(
                        (key in ml_structure["pipelines"][0].keys()),
                        f"Key {key} was not found and expected in the returned dictionary",
                    )
        for model in self.ml_dict["models"]:
            for key in model:
                if key != "Accuracy" and key != "endpoint_name":
                    # print(key)
                    self.assertTrue(
                        (key in ml_structure["models"][0].keys()),
                        f"Key {key} was not found and expected in the returned dictionary",
                    )

    def test_get_ml_structure_eeror(self):
        """
        Test the get version function.
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        with self.assertRaises(nachet.MLRetrievalError):
            asyncio.run(nachet.get_ml_structure(mock_cursor))


class test_picture(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.connection_str = BLOB_CONNECTION_STRING
        self.user_email = "testing@email"
        self.user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.pic_encoded = self.image.tobytes()
        self.pictures = [self.pic_encoded, self.pic_encoded, self.pic_encoded]
        # self.picture_hash= asyncio.run(azure_storage.generate_hash(self.pic_encoded))
        self.container_name = "test-container"
        self.user_id = datastore.User.get_id(self.user_obj)
        self.container_client = asyncio.run(
            datastore.get_user_container_client(
                self.user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        self.seed_name = "test-name"
        self.seed_id = seed_query.new_seed(self.cursor, self.seed_name)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "inference_result.json")
        with open(file_path) as file:
            self.inference = json.load(file)
        self.folder_name = "test_folder"

    def tearDown(self):
        self.con.rollback()
        self.container_client.delete_container()
        db.end_query(self.con, self.cursor)

    def test_upload_picture_unknown(self):
        """
        Test the upload picture function.
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        self.assertTrue(validator.is_valid_uuid(picture_id))

    def test_register_inference_result(self):
        """
        Test the register inference result function.
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        model_id = "test_model_id"

        result = asyncio.run(
            nachet.register_inference_result(
                self.cursor, self.user_id, self.inference, picture_id, model_id
            )
        )
        # self.cursor.execute("SELECT result FROM inference WHERE picture_id=%s AND model_id=%s",(picture_id,model_id,))
        self.assertTrue(validator.is_valid_uuid(result["inference_id"]))

    def test_upload_picture_known(self):
        """
        Test the upload picture function with a known seed
        """
        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id
            )
        )
        picture_id = asyncio.run(
            nachet.upload_picture_known(
                self.cursor,
                self.user_id,
                self.pic_encoded,
                self.container_client,
                self.seed_id,
                picture_set_id,
            )
        )
        self.assertTrue(validator.is_valid_uuid(picture_id))

    def test_upload_picture_known_error_user_not_found(self):
        """
        This test checks if the upload_picture_known function correctly raise an exception if the user given doesn't exist in db
        """
        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id
            )
        )
        with self.assertRaises(nachet.user.UserNotFoundError):
            asyncio.run(
                nachet.upload_picture_known(
                    self.cursor,
                    uuid.uuid4(),
                    self.pic_encoded,
                    self.container_client,
                    self.seed_id,
                    picture_set_id,
                )
            )

    def test_upload_picture_known_connection_error(self):
        """
        This test checks if the upload_picture_known function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id
            )
        )
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.upload_picture_known(
                    mock_cursor,
                    self.user_id,
                    self.pic_encoded,
                    self.container_client,
                    self.seed_id,
                    picture_set_id,
                )
            )

    def test_get_picture_inference(self):
        """
        This test checks if the get_picture_inference function correctly returns the inference of a picture
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        inference = asyncio.run(
            nachet.register_inference_result(
                self.cursor, self.user_id, self.inference, picture_id, "test_model_id"
            )
        )
        for box in inference["boxes"]:
            box["is_verified"] = False

        picture_inference = asyncio.run(
            nachet.get_picture_inference(
                self.cursor, str(self.user_id), str(picture_id)
            )
        )

        self.assertDictEqual(picture_inference, inference)

    def test_get_picture_inference_by_inference_id(self):
        """
        This test checks if the get_picture_inference function correctly returns the inference of a picture
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        inference = asyncio.run(
            nachet.register_inference_result(
                self.cursor, self.user_id, self.inference, picture_id, "test_model_id"
            )
        )
        for box in inference["boxes"]:
            box["is_verified"] = False

        picture_inference = asyncio.run(
            nachet.get_picture_inference(
                self.cursor,
                str(self.user_id),
                inference_id=str(inference["inference_id"]),
            )
        )

        self.assertDictEqual(picture_inference, inference)

    def test_get_picture_inference_error_missing_arguments(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if picture_id and inference_id are not provided
        """
        with self.assertRaises(ValueError):
            asyncio.run(nachet.get_picture_inference(self.cursor, str(uuid.uuid4())))

    def test_get_picture_inference_error_user_not_found(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the user given doesn't exist in db
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                nachet.get_picture_inference(
                    self.cursor, str(uuid.uuid4()), str(picture_id)
                )
            )

    def test_get_picture_inference_error_connection_error(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the connection to the db fails
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.get_picture_inference(
                    mock_cursor, str(self.user_id), str(picture_id)
                )
            )

    def test_get_picture_inference_error_picture_not_found(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the picture given doesn't exist in db
        """
        with self.assertRaises(datastore.picture.PictureNotFoundError):
            asyncio.run(
                nachet.get_picture_inference(
                    self.cursor, str(self.user_id), str(uuid.uuid4())
                )
            )

    def test_get_picture_inference_error_not_owner(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the user is not the owner of the picture set
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )

        not_owner_user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, "notowner@email", self.connection_str, "test-user"
            )
        )
        not_owner_user_id = datastore.User.get_id(not_owner_user_obj)

        with self.assertRaises(nachet.UserNotOwnerError):
            asyncio.run(
                nachet.get_picture_inference(
                    self.cursor, str(not_owner_user_id), str(picture_id)
                )
            )

        container_client = asyncio.run(
            datastore.get_user_container_client(
                not_owner_user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        container_client.delete_container()

    def test_get_picture_blob(self):
        """
        This test checks if the get_picture_blob function correctly returns the blob of a picture
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        blob = asyncio.run(
            nachet.get_picture_blob(
                self.cursor, str(self.user_id), self.container_client, str(picture_id)
            )
        )
        blob_image = Image.frombytes("RGB", (1980, 1080), blob)

        difference = ImageChops.difference(blob_image, self.image)
        self.assertTrue(difference.getbbox() is None)

    def test_get_picture_blob_error_user_not_found(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the user given doesn't exist in db
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                nachet.get_picture_blob(
                    self.cursor,
                    str(uuid.uuid4()),
                    self.container_client,
                    str(picture_id),
                )
            )

    def test_get_picture_blob_error_connection_error(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the connection to the db fails
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.get_picture_blob(
                    mock_cursor,
                    str(self.user_id),
                    self.container_client,
                    str(picture_id),
                )
            )

    def test_get_picture_blob_error_picture_set_not_found(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the picture set given doesn't exist in db
        """
        with self.assertRaises(datastore.picture.PictureNotFoundError):
            asyncio.run(
                nachet.get_picture_blob(
                    self.cursor,
                    str(self.user_id),
                    self.container_client,
                    str(uuid.uuid4()),
                )
            )

    def test_get_picture_blob_error_not_owner(self):
        """
        This test checks if the get_pictures_inferences function correctly raise an exception if the user is not the owner of the picture set
        """
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )

        not_owner_user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, "notowner@email", self.connection_str, "test-user"
            )
        )
        not_owner_user_id = datastore.User.get_id(not_owner_user_obj)

        with self.assertRaises(nachet.UserNotOwnerError):
            asyncio.run(
                nachet.get_picture_blob(
                    self.cursor,
                    str(not_owner_user_id),
                    self.container_client,
                    str(picture_id),
                )
            )

        container_client = asyncio.run(
            datastore.get_user_container_client(
                not_owner_user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        container_client.delete_container()


class test_picture_set(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.connection_str = BLOB_CONNECTION_STRING
        self.user_email = "testingss@email"
        self.user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.pic_encoded = self.image.tobytes()
        # self.picture_hash= asyncio.run(azure_storage.generate_hash(self.pic_encoded))
        self.container_name = "test-container"
        self.user_id = datastore.User.get_id(self.user_obj)
        self.container_client = asyncio.run(
            datastore.get_user_container_client(
                self.user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        self.seed_name = "test-name"
        self.seed_id = seed_query.new_seed(self.cursor, self.seed_name)
        self.folder_name = "test_folder"
        self.picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id, self.folder_name
            )
        )
        self.pictures_ids = asyncio.run(
            datastore.upload_pictures(
                self.cursor,
                self.user_id,
                [self.pic_encoded, self.pic_encoded, self.pic_encoded],
                self.container_client,
                self.picture_set_id,
            )
        )
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "inference_result.json")
        with open(file_path) as file:
            self.inference = json.load(file)

        self.dev_user_id = datastore.user.get_user_id(
            self.cursor, os.environ["DEV_USER_EMAIL"]
        )
        self.dev_container_client = asyncio.run(
            datastore.get_user_container_client(
                self.dev_user_id, BLOB_CONNECTION_STRING, BLOB_ACCOUNT, BLOB_KEY
            )
        )

    def tearDown(self):
        self.con.rollback()
        self.container_client.delete_container()
        db.end_query(self.con, self.cursor)

    def test_get_picture_sets_info(self):
        """
        Test the get_picture_sets_info function
        """

        picture_sets_info = asyncio.run(
            nachet.get_picture_sets_info(self.cursor, self.user_id)
        )

        self.assertEqual(len(picture_sets_info), 2)

        for picture_set in picture_sets_info:
            if picture_set["picture_set_id"] == self.picture_set_id:
                expected_pictures_info = [
                    {"picture_id": pid, "is_verified": False, "inference_exist": False}
                    for pid in self.pictures_id
                ]
                self.assert_picture_set_info(
                    picture_set,
                    self.picture_set_id,
                    self.folder_name,
                    3,
                    expected_pictures_info,
                )

        self.picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor,
                self.container_client,
                0,
                self.user_id,
                self.folder_name + "2",
            )
        )
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor,
                self.user_id,
                self.pic_encoded,
                self.container_client,
                self.picture_set_id,
            )
        )
        inference = asyncio.run(
            nachet.register_inference_result(
                self.cursor, self.user_id, self.inference, picture_id, "test_model_id"
            )
        )
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inference["inference_id"],
                self.user_id,
                [box["box_id"] for box in inference["boxes"]],
            )
        )

        picture_sets_info = asyncio.run(
            nachet.get_picture_sets_info(self.cursor, self.user_id)
        )

        self.assertEqual(len(picture_sets_info), 3)

        for picture_set in picture_sets_info:
            if picture_set["picture_set_id"] == self.picture_set_id:
                expected_pictures_info = [
                    {
                        "picture_id": picture_id,
                        "is_verified": True,
                        "inference_exist": True,
                    }
                ]
                self.assert_picture_set_info(
                    picture_set,
                    self.picture_set_id,
                    self.folder_name + "2",
                    1,
                    expected_pictures_info,
                )

    def test_get_picture_sets_info_error_user_not_found(self):
        """
        This test checks if the get_picture_sets_info function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(nachet.get_picture_sets_info(self.cursor, uuid.uuid4()))

    def test_get_picture_sets_info_error_connection_error(self):
        """
        This test checks if the get_picture_sets_info function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(nachet.get_picture_sets_info(mock_cursor, self.user_id))

    def test_find_validated_pictures(self):
        """
        This test checks if the find_validated_pictures function correctly returns the validated pictures of a picture_set
        """

        self.assertEqual(
            len(
                asyncio.run(
                    nachet.find_validated_pictures(
                        self.cursor, str(self.user_id), str(self.picture_set_id)
                    )
                )
            ),
            0,
            "No validated pictures should be found",
        )

        inferences = []
        for picture_id in self.pictures_ids:
            # Using deepcopy to ensure each inference is a unique object without shared references
            inference_copy = deepcopy(self.inference)
            inference = asyncio.run(
                nachet.register_inference_result(
                    self.cursor,
                    self.user_id,
                    inference_copy,
                    picture_id,
                    "test_model_id",
                )
            )
            inferences.append(inference)

        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inferences[0]["inference_id"],
                self.user_id,
                [box["box_id"] for box in inferences[0]["boxes"]],
            )
        )

        self.assertEqual(
            len(
                asyncio.run(
                    nachet.find_validated_pictures(
                        self.cursor, str(self.user_id), str(self.picture_set_id)
                    )
                )
            ),
            1,
            "One validated pictures should be found",
        )

        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inferences[1]["inference_id"],
                self.user_id,
                [box["box_id"] for box in inferences[1]["boxes"]],
            )
        )
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inferences[2]["inference_id"],
                self.user_id,
                [box["box_id"] for box in inferences[2]["boxes"]],
            )
        )

        self.assertEqual(
            len(
                asyncio.run(
                    nachet.find_validated_pictures(
                        self.cursor, str(self.user_id), str(self.picture_set_id)
                    )
                )
            ),
            3,
            "One validated pictures should be found",
        )

    def test_find_validated_pictures_error_user_not_found(self):
        """
        This test checks if the find_validated_pictures function correctly raise an exception if the user given doesn't exist in db
        """
        pictures_id = []
        for i in range(3):
            picture_id = asyncio.run(
                nachet.upload_picture_unknown(
                    self.cursor,
                    self.user_id,
                    self.pic_encoded,
                    self.container_client,
                    self.picture_set_id,
                )
            )
            pictures_id.append(picture_id)

        with self.assertRaises(nachet.user.UserNotFoundError):
            asyncio.run(
                nachet.find_validated_pictures(
                    self.cursor, str(uuid.uuid4()), str(self.picture_set_id)
                )
            )

    def test_find_validated_pictures_error_connection_error(self):
        """
        This test checks if the find_validated_pictures function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.find_validated_pictures(
                    mock_cursor, str(self.user_id), str(self.picture_set_id)
                )
            )

    def test_find_validated_pictures_error_picture_set_not_found(self):
        """
        This test checks if the find_validated_pictures function correctly raise an exception if the picture set given doesn't exist in db
        """
        with self.assertRaises(nachet.picture.PictureSetNotFoundError):
            asyncio.run(
                nachet.find_validated_pictures(
                    self.cursor, str(self.user_id), str(uuid.uuid4())
                )
            )

    def test_find_validated_pictures_error_not_owner(self):
        """
        This test checks if the find_validated_pictures function correctly raise an exception if the user is not the owner of the picture set
        """
        not_owner_user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, "notowner@email", self.connection_str, "test-user"
            )
        )
        not_owner_user_id = datastore.User.get_id(not_owner_user_obj)

        with self.assertRaises(nachet.UserNotOwnerError):
            asyncio.run(
                nachet.find_validated_pictures(
                    self.cursor, str(not_owner_user_id), str(self.picture_set_id)
                )
            )

        container_client = asyncio.run(
            datastore.get_user_container_client(
                not_owner_user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        container_client.delete_container()

    def test_delete_picture_set_with_archive(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly archive the picture set in dev container and delete it from user container
        """
        # Create inferences for pictures in the picture set
        inferences = []
        for picture_id in self.pictures_ids:
            # Using deepcopy to ensure each inference is a unique object without shared references
            inference_copy = deepcopy(self.inference)
            inference = asyncio.run(
                nachet.register_inference_result(
                    self.cursor,
                    self.user_id,
                    inference_copy,
                    picture_id,
                    "test_model_id",
                )
            )
            inferences.append(inference)
        # Validate 2 of 3 pictures in the picture set
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inferences[1]["inference_id"],
                self.user_id,
                [box["box_id"] for box in inferences[1]["boxes"]],
            )
        )
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor,
                inferences[2]["inference_id"],
                self.user_id,
                [box["box_id"] for box in inferences[2]["boxes"]],
            )
        )
        validated_pictures = asyncio.run(
            nachet.find_validated_pictures(
                self.cursor, str(self.user_id), str(self.picture_set_id)
            )
        )

        dev_nb_folders = len(
            asyncio.run(nachet.get_picture_sets_info(self.cursor, self.dev_user_id))
        )
        # Check there is the right number of picture sets in db for each user
        self.assertEqual(
            len(asyncio.run(nachet.get_picture_sets_info(self.cursor, self.user_id))),
            2,
        )

        dev_picture_set_id = asyncio.run(
            nachet.delete_picture_set_with_archive(
                self.cursor,
                str(self.user_id),
                str(self.picture_set_id),
                self.container_client,
            )
        )
        # Check there is the right number of picture sets in db for each user after moving
        self.assertEqual(
            len(asyncio.run(nachet.get_picture_sets_info(self.cursor, self.user_id))),
            1,
        )
        self.assertEqual(
            len(
                asyncio.run(nachet.get_picture_sets_info(self.cursor, self.dev_user_id))
            ),
            dev_nb_folders + 1,
        )

        # Check blobs have also moved in blob storage
        for picture_id in validated_pictures:
            blob_name = datastore.azure_storage.build_blob_name(
                self.folder_name, str(picture_id)
            )
            with self.assertRaises(Exception):
                asyncio.run(
                    datastore.azure_storage.get_blob(self.container_client, blob_name)
                )

            dev_blob_name = datastore.azure_storage.build_blob_name(
                str(self.user_id), blob_name
            )
            blob = asyncio.run(
                datastore.azure_storage.get_blob(
                    self.dev_container_client, dev_blob_name
                )
            )
            self.assertEqual(blob, self.pic_encoded)

        # TEAR DOWN
        # Delete the user folder in the blob storage
        asyncio.run(
            datastore.azure_storage.delete_folder(
                self.dev_container_client, str(dev_picture_set_id)
            )
        )
        asyncio.run(
            datastore.azure_storage.delete_folder(
                self.dev_container_client, str(self.user_id)
            )
        )

    def test_delete_picture_set_with_archive_error_user_not_found(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(nachet.user.UserNotFoundError):
            asyncio.run(
                nachet.delete_picture_set_with_archive(
                    self.cursor,
                    str(uuid.uuid4()),
                    str(self.picture_set_id),
                    self.container_client,
                )
            )

    def test_delete_picture_set_with_archive_error_connection_error(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.delete_picture_set_with_archive(
                    mock_cursor,
                    str(self.user_id),
                    str(self.picture_set_id),
                    self.container_client,
                )
            )

    def test_delete_picture_set_with_archive_error_picture_set_not_found(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly raise an exception if the picture set given doesn't exist in db
        """
        with self.assertRaises(nachet.picture.PictureSetNotFoundError):
            asyncio.run(
                nachet.delete_picture_set_with_archive(
                    self.cursor,
                    str(self.user_id),
                    str(uuid.uuid4()),
                    self.container_client,
                )
            )

    def test_delete_picture_set_with_archive_error_not_owner(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly raise an exception if the user is not the owner of the picture set
        """
        not_owner_user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, "notowner@email", self.connection_str, "test-user"
            )
        )
        not_owner_user_id = datastore.User.get_id(not_owner_user_obj)

        with self.assertRaises(nachet.UserNotOwnerError):
            asyncio.run(
                nachet.delete_picture_set_with_archive(
                    self.cursor,
                    str(not_owner_user_id),
                    str(self.picture_set_id),
                    self.container_client,
                )
            )

        container_client = asyncio.run(
            datastore.get_user_container_client(
                not_owner_user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        container_client.delete_container()

    def test_delete_picture_set_with_archive_error_default_folder(self):
        """
        This test checks if the delete_picture_set_with_archive function correctly raise an exception if the user want to delete the folder "General"
        """
        general_folder_id = datastore.user.get_default_picture_set(
            self.cursor, self.user_id
        )
        with self.assertRaises(nachet.picture.PictureSetDeleteError):
            asyncio.run(
                nachet.delete_picture_set_with_archive(
                    self.cursor,
                    str(self.user_id),
                    str(general_folder_id),
                    self.container_client,
                )
            )


class test_feedback(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.connection_str = BLOB_CONNECTION_STRING
        self.user_email = "test@email"
        self.user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        self.image = Image.new("RGB", (1980, 1080), "blue")
        self.image_byte_array = io.BytesIO()
        self.image.save(self.image_byte_array, format="TIFF")
        self.pic_encoded = self.image.tobytes()
        self.container_name = "test-container"
        self.user_id = datastore.User.get_id(self.user_obj)
        self.container_client = asyncio.run(
            datastore.get_user_container_client(
                self.user_id,
                BLOB_CONNECTION_STRING,
                BLOB_ACCOUNT,
                BLOB_KEY,
                "test-user",
            )
        )
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "inference_result.json")
        with open(file_path) as file:
            self.inference = json.load(file)
        picture_id = asyncio.run(
            nachet.upload_picture_unknown(
                self.cursor, self.user_id, self.pic_encoded, self.container_client
            )
        )
        model_id = "test_model_id"
        self.registered_inference = asyncio.run(
            nachet.register_inference_result(
                self.cursor, self.user_id, self.inference, picture_id, model_id
            )
        )
        self.registered_inference["user_id"] = self.user_id
        self.mock_box = {"topX": 123, "topY": 456, "bottomX": 789, "bottomY": 123}
        self.inference_id = self.registered_inference.get("inference_id")
        self.boxes_id = []
        self.top_id = []
        self.unreal_seed_id = nachet.seed.new_seed(self.cursor, "unreal_seed")
        for box in self.registered_inference["boxes"]:
            self.boxes_id.append(box["box_id"])
            self.top_id.append(box["top_id"])
            box["classId"] = nachet.seed.get_seed_id(self.cursor, box["label"])

    def tearDown(self):
        self.con.rollback()
        self.container_client.delete_container()
        db.end_query(self.con, self.cursor)

    def test_new_perfect_inference_feedback(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly updates the inference object after a perfect feedback is given
        """
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor, self.inference_id, self.user_id, self.boxes_id
            )
        )
        for i in range(len(self.boxes_id)):
            object = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must be equal to top_id
            self.assertEqual(str(object[4]), self.top_id[i])
            # valid column must be true
            self.assertTrue(object[5])

    def test_new_perfect_inference_feedback_error_verified_inference(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly raise an exception if the inference given is already verified
        """
        asyncio.run(
            nachet.new_perfect_inference_feeback(
                self.cursor, self.inference_id, self.user_id, self.boxes_id
            )
        )
        self.assertTrue(
            nachet.inference.is_inference_verified(self.cursor, self.inference_id)
        )
        with self.assertRaises(nachet.inference.InferenceAlreadyVerifiedError):
            asyncio.run(
                nachet.new_perfect_inference_feeback(
                    self.cursor, self.inference_id, self.user_id, self.boxes_id
                )
            )

    def test_new_perfect_inference_feedback_error_inference_not_found(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly raise an exception if the inference given doesn't exist in db
        """
        with self.assertRaises(nachet.inference.InferenceNotFoundError):
            asyncio.run(
                nachet.new_perfect_inference_feeback(
                    self.cursor, str(uuid.uuid4()), self.user_id, self.boxes_id
                )
            )

    def test_new_perfect_inference_feedback_error_inference_object_not_found(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly raise an exception if one of the inference object given doesn't exist in db
        """
        with self.assertRaises(nachet.inference.InferenceObjectNotFoundError):
            asyncio.run(
                nachet.new_perfect_inference_feeback(
                    self.cursor,
                    self.inference_id,
                    self.user_id,
                    [self.boxes_id[0], str(uuid.uuid4())],
                )
            )

    def test_new_perfect_inference_feedback_error_user_not_found(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(nachet.user.UserNotFoundError):
            asyncio.run(
                nachet.new_perfect_inference_feeback(
                    self.cursor, self.inference_id, str(uuid.uuid4()), self.boxes_id
                )
            )

    def test_new_perfect_inference_feedback_connection_error(self):
        """
        This test checks if the new_perfect_inference_feeback function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                nachet.new_perfect_inference_feeback(
                    mock_cursor, self.inference_id, self.user_id, self.boxes_id
                )
            )

    def test_new_correction_inference_feedback(self):
        """
        This test checks if the new_correction_inference_feeback function correctly
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for i in range(len(self.boxes_id)):
            object = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must be equal to top_id
            self.assertEqual(str(object[4]), self.top_id[i])
            # valid column must be true
            self.assertTrue(object[6])

    def test_new_correction_inference_feedback_new_guess(self):
        """
        This test checks if the new_correction_inference_feeback function correctly when another guess is verified
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        new_top_ids = []
        for box in self.registered_inference["boxes"]:
            box["label"] = box["topN"][1]["label"]
            box["classId"] = nachet.seed.get_seed_id(self.cursor, box["label"])
            new_top_ids.append(box["topN"][1]["object_id"])
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for i in range(len(self.boxes_id)):
            object_db = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must be equal to top_id
            self.assertTrue(str(object_db[4]) == new_top_ids[i])
            # valid column must be true
            self.assertTrue(object_db[6])

    def test_new_correction_inference_feedback_box_edited(self):
        """
        This test checks if the new_correction_inference_feeback function correctly when the box metadata is updated
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        for box in self.registered_inference["boxes"]:
            box["box"] = self.mock_box
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for box in self.registered_inference["boxes"]:
            object_db = nachet.inference.get_inference_object(
                self.cursor, box["box_id"]
            )
            # The new box metadata must be updated
            self.assertDictEqual(object_db[1], self.mock_box)
            # The top_id must be equal to the previous top_id
            self.assertEqual(str(object_db[4]), box["top_id"])
            # valid column must be true
            self.assertTrue(object_db[6])

    def test_new_correction_inference_feedback_not_guess(self):
        """
        This test checks if the new_correction_inference_feeback function correctly when the box is not a guess
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        for box in self.registered_inference["boxes"]:
            box["label"] = "unreal_seed"
            box["classId"] = self.unreal_seed_id
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for i in range(len(self.boxes_id)):
            object_db = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must be equal to the new_top_id
            new_top_id = nachet.inference.get_seed_object_id(
                self.cursor, self.unreal_seed_id, object_db[0]
            )
            self.assertTrue(validator.is_valid_uuid(new_top_id))
            self.assertEqual(str(object_db[4]), str(new_top_id))
            # valid column must be true
            self.assertTrue(object_db[6])

    def test_new_correction_inference_feedback_not_valid(self):
        """
        This test checks if the new_correction_inference_feeback function correctly when the box is not a guess
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        for box in self.registered_inference["boxes"]:
            box["label"] = ""
            box["classId"] = ""
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for i in range(len(self.boxes_id)):
            object_db = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must not be an id
            self.assertEqual(object_db[4], None)
            # valid column must be false
            self.assertFalse(object_db[6])

    def test_new_correction_inference_feedback_unknown_seed(self):
        """
        This test checks if the new_correction_inference_feeback function correctly when the box is not a guess
        """
        self.assertTrue(validator.is_valid_uuid(self.inference_id))
        for box in self.registered_inference["boxes"]:
            box["label"] = "unknown_seed"
            box["classId"] = ""
        # temporary fix until we fix FE
        self.registered_inference["inferenceId"] = self.inference_id
        self.registered_inference["userId"] = self.user_id
        for box in self.registered_inference["boxes"]:
            box["boxId"] = box["box_id"]
        asyncio.run(
            nachet.new_correction_inference_feedback(
                self.cursor, self.registered_inference, 1
            )
        )
        for i in range(len(self.boxes_id)):
            object_db = nachet.inference.get_inference_object(
                self.cursor, self.boxes_id[i]
            )
            # verified_id must be equal to an id
            self.assertTrue(validator.is_valid_uuid(str(object_db[4])))
            # valid column must be true
            self.assertTrue(object_db[6])
