"""
This is a test script for the highest level of the datastore packages.
It tests the functions in the __init__.py files of the datastore packages.
"""

import asyncio
import io
import os
import unittest
import uuid
from unittest.mock import MagicMock, patch

from PIL import Image

import datastore.__init__ as datastore
import datastore.db.__init__ as db
import datastore.db.metadata.validator as validator

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")

BLOB_CONNECTION_STRING = os.environ["NACHET_STORAGE_URL_TESTING"]
if BLOB_CONNECTION_STRING is None or BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL_TESTING is not set")

BLOB_ACCOUNT = os.environ["NACHET_BLOB_ACCOUNT_TESTING"]
if BLOB_ACCOUNT is None or BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

BLOB_KEY = os.environ["NACHET_BLOB_KEY_TESTING"]
if BLOB_KEY is None or BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")


class test_user(unittest.TestCase):
    def setUp(self):
        self.con = db.connect_db(DB_CONNECTION_STRING, DB_SCHEMA)
        self.cursor = self.con.cursor()
        db.create_search_path(self.con, self.cursor, DB_SCHEMA)
        self.user_email = "testssssss@email"
        self.user_id = None
        self.connection_str = BLOB_CONNECTION_STRING

    def tearDown(self):
        self.con.rollback()
        if self.user_id is not None:
            self.container_client = asyncio.run(
                datastore.get_user_container_client(
                    self.user_id,
                    BLOB_CONNECTION_STRING,
                    BLOB_ACCOUNT,
                    BLOB_KEY,
                    "test-user",
                )
            )
            self.container_client.delete_container()
        self.user_id = None
        db.end_query(self.con, self.cursor)

    def test_new_user(self):
        """
        Test the new user function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        self.assertIsInstance(user_obj, datastore.User)
        # self.user_id=user_obj.id
        self.user_id = datastore.User.get_id(user_obj)
        self.assertTrue(validator.is_valid_uuid(self.user_id))
        self.assertEqual(datastore.User.get_email(user_obj), self.user_email)

    def test_already_existing_user(self):
        """
        Test the already existing user function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        self.user_id = datastore.User.get_id(user_obj)
        self.assertTrue(validator.is_valid_uuid(self.user_id))
        with self.assertRaises(datastore.UserAlreadyExistsError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, "test-user"
                )
            )

    @patch("azure.storage.blob.ContainerClient.exists")
    def test_new_user_container_error(self, MockExists):
        """
        Test the new user container error function.
        """
        MockExists.return_value = False
        with self.assertRaises(datastore.ContainerCreationError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, "test-user"
                )
            )

    @patch("datastore.blob.azure_storage_api.create_folder")
    def test_new_user_folder_error(self, MockCreateFolder):
        """
        Test the new user folder error function.
        """
        MockCreateFolder.side_effect = datastore.azure_storage.CreateDirectoryError(
            "Test error"
        )
        with self.assertRaises(datastore.FolderCreationError):
            asyncio.run(
                datastore.new_user(
                    self.cursor, self.user_email, self.connection_str, "test-user"
                )
            )

    def test_get_User(self):
        """
        Test the get User object function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        user_id = datastore.User.get_id(user_obj)
        user_get = asyncio.run(datastore.get_user(self.cursor, self.user_email))
        user_get_id = datastore.User.get_id(user_get)
        self.assertEqual(user_id, user_get_id)
        self.assertEqual(
            datastore.User.get_email(user_obj), datastore.User.get_email(user_get)
        )

    def test_get_user_container_client(self):
        """
        Test the get user container client function.
        """
        user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, self.user_email, self.connection_str, "test-user"
            )
        )
        user_id = datastore.User.get_id(user_obj)
        container_client = asyncio.run(
            datastore.get_user_container_client(
                user_id, BLOB_CONNECTION_STRING, BLOB_ACCOUNT, BLOB_KEY, "test-user"
            )
        )
        self.assertTrue(container_client.exists())


class test_picture(unittest.TestCase):
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
        self.folder_name = "test_folder"
        self.picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 3, self.user_id, self.folder_name
            )
        )

    def tearDown(self):
        self.con.rollback()
        self.container_client.delete_container()
        db.end_query(self.con, self.cursor)

    def test_upload_pictures(self):
        """
        Test the upload pictures function
        """
        pictures = [self.pic_encoded, self.pic_encoded, self.pic_encoded]
        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id
            )
        )
        picture_ids = asyncio.run(
            datastore.upload_pictures(
                self.cursor,
                self.user_id,
                pictures,
                self.container_client,
                picture_set_id,
            )
        )
        self.assertTrue(
            all([validator.is_valid_uuid(picture_id) for picture_id in picture_ids])
        )
        self.assertEqual(
            len(pictures),
            asyncio.run(
                datastore.azure_storage.get_image_count(
                    self.container_client, str(picture_set_id)
                )
            ),
        )
        self.assertTrue(
            len(pictures),
            (datastore.picture.count_pictures(self.cursor, picture_set_id)),
        )

    def test_upload_pictures_error_user_not_found(self):
        """
        This test checks if the upload_picture_known function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                datastore.upload_pictures(
                    self.cursor,
                    str(uuid.uuid4()),
                    self.pic_encoded,
                    self.container_client,
                )
            )

    def test_create_picture_set(self):
        """
        Test the creation of a picture set
        """
        picture_set_id = asyncio.run(
            datastore.create_picture_set(
                self.cursor, self.container_client, 0, self.user_id
            )
        )
        self.assertTrue(validator.is_valid_uuid(picture_set_id))

    def test_create_picture_set_connection_error(self):
        """
        This test checks if the create_picture_set function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                datastore.create_picture_set(
                    mock_cursor, self.container_client, 0, self.user_id
                )
            )

    def test_create_picture_set_error_user_not_found(self):
        """
        This test checks if the create_picture_set function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                datastore.create_picture_set(
                    self.cursor, self.container_client, 0, uuid.uuid4()
                )
            )

    def test_get_picture_sets_info(self):
        """
        Test the get_picture_sets_info function
        """
        picture_ids = asyncio.run(
            datastore.upload_pictures(
                self.cursor,
                self.user_id,
                [self.pic_encoded, self.pic_encoded, self.pic_encoded],
                self.container_client,
                self.picture_set_id,
            )
        )
        picture_sets_info = asyncio.run(
            datastore.get_picture_sets_info(self.cursor, self.user_id)
        )
        self.assertEqual(len(picture_sets_info), 2)
        self.assertEqual(
            picture_sets_info.get(str(self.picture_set_id))[1], len(picture_ids)
        )
        self.assertEqual(
            picture_sets_info.get(str(self.picture_set_id))[0], self.folder_name
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

        picture_sets_info = asyncio.run(
            datastore.get_picture_sets_info(self.cursor, self.user_id)
        )
        self.assertEqual(len(picture_sets_info), 3)
        self.assertEqual(picture_sets_info.get(str(self.picture_set_id))[1], 0)
        self.assertEqual(
            picture_sets_info.get(str(self.picture_set_id))[0], self.folder_name + "2"
        )

    def test_get_picture_sets_info_error_user_not_found(self):
        """
        This test checks if the get_picture_sets_info function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(datastore.get_picture_sets_info(self.cursor, uuid.uuid4()))

    def test_get_picture_sets_info_error_connection_error(self):
        """
        This test checks if the get_picture_sets_info function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(datastore.get_picture_sets_info(mock_cursor, self.user_id))

    def test_delete_picture_set_permanently(self):
        """
        This test checks the delete_picture_set_permanently function
        """
        picture_sets_info = asyncio.run(
            datastore.get_picture_sets_info(self.cursor, self.user_id)
        )
        self.assertEqual(len(picture_sets_info), 2)
        asyncio.run(
            datastore.delete_picture_set_permanently(
                self.cursor,
                str(self.user_id),
                str(self.picture_set_id),
                self.container_client,
            )
        )

        picture_sets_info = asyncio.run(
            datastore.get_picture_sets_info(self.cursor, self.user_id)
        )
        self.assertEqual(len(picture_sets_info), 1)

    def test_delete_picture_set_permanently_error_user_not_found(self):
        """
        This test checks if the delete_picture_set_permanently function correctly raise an exception if the user given doesn't exist in db
        """

        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                datastore.delete_picture_set_permanently(
                    self.cursor,
                    str(uuid.uuid4()),
                    str(self.picture_set_id),
                    self.container_client,
                )
            )

    def test_delete_picture_set_permanently_error_connection_error(self):
        """
        This test checks if the delete_picture_set_permanently function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                datastore.delete_picture_set_permanently(
                    mock_cursor,
                    str(self.user_id),
                    str(self.picture_set_id),
                    self.container_client,
                )
            )

    def test_delete_picture_set_permanently_error_picture_set_not_found(self):
        """
        This test checks if the delete_picture_set_permanently function correctly raise an exception if the picture set given doesn't exist in db
        """
        with self.assertRaises(datastore.picture.PictureSetNotFoundError):
            asyncio.run(
                datastore.delete_picture_set_permanently(
                    self.cursor,
                    str(self.user_id),
                    str(uuid.uuid4()),
                    self.container_client,
                )
            )

    def test_delete_picture_set_permanently_error_not_owner(self):
        """
        This test checks if the delete_picture_set_permanently function correctly raise an exception if the user is not the owner of the picture set
        """
        not_owner_user_obj = asyncio.run(
            datastore.new_user(
                self.cursor, "notowner@email", self.connection_str, "test-user"
            )
        )
        not_owner_user_id = datastore.User.get_id(not_owner_user_obj)

        with self.assertRaises(datastore.UserNotOwnerError):
            asyncio.run(
                datastore.delete_picture_set_permanently(
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

    def test_delete_picture_set_permanently_error_default_folder(self):
        """
        This test checks if the delete_picture_set_permanently function correctly raise an exception if the user want to delete the folder "General"
        """
        general_folder_id = datastore.user.get_default_picture_set(
            self.cursor, self.user_id
        )
        with self.assertRaises(datastore.picture.PictureSetDeleteError):
            asyncio.run(
                datastore.delete_picture_set_permanently(
                    self.cursor,
                    str(self.user_id),
                    str(general_folder_id),
                    self.container_client,
                )
            )

    def test_get_picture_set_pictures(self):
        """
        This test checks the get_picture_set_pictures function
        """
        picture_ids = asyncio.run(
            datastore.upload_pictures(
                self.cursor,
                self.user_id,
                [self.pic_encoded, self.pic_encoded, self.pic_encoded],
                self.container_client,
                self.picture_set_id,
            )
        )
        pictures = asyncio.run(
            datastore.get_picture_set_pictures(
                self.cursor, self.user_id, self.picture_set_id, self.container_client
            )
        )
        self.assertEqual(len(pictures), 3)
        for picture in pictures:
            self.assertTrue(picture["id"] in picture_ids)

    def test_get_picture_set_pictures_error_user_not_found(self):
        """
        This test checks if the get_picture_set_pictures function correctly raise an exception if the user given doesn't exist in db
        """
        with self.assertRaises(datastore.user.UserNotFoundError):
            asyncio.run(
                datastore.get_picture_set_pictures(
                    self.cursor,
                    str(uuid.uuid4()),
                    self.picture_set_id,
                    self.container_client,
                )
            )

    def test_get_picture_set_pictures_error_connection_error(self):
        """
        This test checks if the get_picture_set_pictures function correctly raise an exception if the connection to the db fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(Exception):
            asyncio.run(
                datastore.get_picture_set_pictures(
                    mock_cursor,
                    self.user_id,
                    self.picture_set_id,
                    self.container_client,
                )
            )

    def test_get_picture_set_pictures_error_picture_set_not_found(self):
        """
        This test checks if the get_picture_set_pictures function correctly raise an exception if the picture set given doesn't exist in db
        """
        with self.assertRaises(datastore.picture.PictureSetNotFoundError):
            asyncio.run(
                datastore.get_picture_set_pictures(
                    self.cursor, self.user_id, str(uuid.uuid4()), self.container_client
                )
            )


if __name__ == "__main__":
    unittest.main()
