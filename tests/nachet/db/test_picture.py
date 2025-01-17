"""
This is a test script for the database packages. 
It tests the functions in the user, seed and picture modules.
"""

import unittest
import uuid
import os
from PIL import Image
import io
import base64
from unittest.mock import MagicMock

import datastore.db.__init__ as db
from nachet.db.metadata import picture as picture_data
from datastore.db.metadata import picture_set as picture_set_data
from datastore.db.metadata import validator
from datastore.db.queries import picture, user
import nachet.db.queries.seed as seed

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
DB_CONNECTION_STRING = f"postgresql://{NACHET_DB_USER}:{NACHET_DB_PASSWORD}@{NACHET_DB_URL}"
if DB_CONNECTION_STRING is None or DB_CONNECTION_STRING == "":
    raise ValueError("NACHET_DB_URL_TESTING is not set")

DB_SCHEMA = os.environ.get("NACHET_SCHEMA_TESTING")
if DB_SCHEMA is None or DB_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA_TESTING is not set")


# --------------------  PICTURE FUNCTIONS --------------------
class test_pictures_functions(unittest.TestCase):
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
        self.nb_seed = 1
        self.picture_set = picture_set_data.build_picture_set_metadata(self.user_id, 1)
        self.picture = picture_data.build_picture(
            self.pic_encoded, "www.link.com", self.nb_seed, 1.0, ""
        )
        self.folder_name = "test_folder"

    def tearDown(self):
        self.con.rollback()
        db.end_query(self.con, self.cursor)

    def test_new_picture(self):
        """
        This test checks if the new_picture function returns a valid UUID
        """
        # prepare the picture_set
        picture_set_id = picture.new_picture_set(
            self.cursor, self.picture_set, self.user_id
        )

        # create the new picture in the db
        picture_id = picture.new_picture(
            self.cursor, self.picture, picture_set_id, self.seed_id, self.nb_seed
        )

        self.assertTrue(
            validator.is_valid_uuid(picture_id), "The picture_id is not a valid UUID"
        )

    def test_new_picture_error(self):
        """
        This test checks if the new_picture function raises an exception when the connection fails
        """
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = Exception("Connection error")
        with self.assertRaises(picture.PictureUploadError):
            picture.new_picture(
                mock_cursor, self.picture, str(uuid.uuid4()), self.seed_id, self.nb_seed
            )
