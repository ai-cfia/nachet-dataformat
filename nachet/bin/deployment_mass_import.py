import sys
import os
import io
import base64
import warnings
from PIL import Image
import nachet.db.queries.seed as seed
import datastore.db.queries.user as user
import datastore.db.queries.picture as picture_query
import datastore.db.metadata.picture_set as picture_set_metadata
import nachet.db.metadata.picture as picture_metadata
import datastore.db.metadata.validator as validator

""" This script is used to import the missing metadata from an Azure container to the database """


# Constants
CONTAINER_URL = ""
SEED_ID = ""


class NonExistingEmail(Exception):
    pass


class UnProcessedFilesWarning(UserWarning):
    pass


class NonExistingSeedName(Exception):
    pass


class MissingArguments(Exception):
    pass


def json_deletion(picture_folder):
    """
    Function to delete all the .json files in the specified folder in case of a bad importation.

    Parameters:
    - picture_folder (str): The path to the folder.
    """
    # Get a list of files in the directory
    files = []
    for f in os.listdir(picture_folder):
        if os.path.isfile(os.path.join(picture_folder, f) and f.endswith(".json")):
            files.append(f)
    # Iterate over the list of filepaths & remove each file.
    for file in files:
        try:
            os.remove(file)
        except OSError as e:
            print("Error: %s : %s" % (file, e.strerror))


def local_import(
    picture_folder: str,
    client_email: str,
    seed_name: str,
    zoom_level: float,
    seed_number: int,
    cur,
):
    """
    Template function to do the importation process of the metadata from the Azure container to the database.
    The user is prompted to input the client email, the zoom level and the number of seeds for the picture_set.
    The container needs to be downloaded locally before running this function.

    Parameters:
    - picture_folder (str): Relative path to the folder we want to import.
    - client_email (str): The email of the client.
    - seed_name (str): The name of the seed
    - zoom_level (float): The zoom level of the picture.
    - seed_number (int): The number of seeds in the picture.
    - cur: The cursor object to interact with the database.
    """

    seed_id = seed.get_seed_id(cursor=cur, seed_name=seed_name)
    if seed_id is None or validator.is_valid_uuid(seed_id) is False:
        seed_list = seed.get_all_seeds_names(cursor=cur)
        print("List of seeds in the database: ")
        for seed_db in seed_list:
            print(seed_db[0])
        raise NonExistingSeedName(
            f"Error: could not retrieve the seed_id based on provided name: {seed_name}"
        )

    user_id = user.get_user_id(cursor=cur, email=client_email)
    if user_id is None or validator.is_valid_uuid(user_id) is False:
        raise NonExistingEmail(
            f"Error: could not retrieve the user_id with the provided email: {client_email}"
        )

    nb_file = len(
        [
            f
            for f in os.listdir(picture_folder)
            if os.path.isfile(os.path.join(picture_folder, f))
        ]
    )
    # build picture_set
    picture_set = picture_set_metadata.build_picture_set_metadata(
        user_id=user_id, nb_picture=nb_file
    )

    # upload picture_set to database
    picture_set_id = picture_query.new_picture_set(
        cursor=cur, picture_set_metadata=picture_set, user_id=user_id
    )

    # Get a list of files in the directory
    files = []
    for f in os.listdir(picture_folder):
        if os.path.isfile(os.path.join(picture_folder, f)):
            files.append(f)

    actual_nb_pic = 0
    # Loop through each file in the folder
    for i, filename in enumerate(files):
        if filename.endswith(".tiff") or filename.endswith(".tif"):
            img = Image.open(f"{picture_folder}/{filename}")
            img_byte_array = io.BytesIO()
            img.save(img_byte_array, format="TIFF")
            img_encoded = base64.b64encode(img_byte_array.getvalue()).decode("utf8")

            image_metadata = picture_metadata.build_picture(
                pic_encoded=img_encoded,
                link=CONTAINER_URL + picture_folder + filename,
                nb_seeds=seed_number,
                zoom=zoom_level,
                description="mass importation",
            )
            picture_query.new_picture(
                cursor=cur,
                picture=image_metadata,
                picture_set_id=picture_set_id,
                seed_id=seed_id,
            )
            # build_picture(picture_folder, seed_number, zoom_level, filename)
            # pic_path = f'{picture_folder}/{filename.removesuffix(".tiff")}.json'
            # upload picture to database
            # upload_picture_db(pic_path, picture_set_id, seed_id=seed_id,cur=cur,conn=conn)
            actual_nb_pic = actual_nb_pic + 1

    if actual_nb_pic != nb_file:
        warnings.warn(" invallid file extension found, only the .TIFF files have been processed", UnProcessedFilesWarning)
    else:
        print("importation of " + picture_folder + " complete")


if __name__ == "__main__":
    local_import(*sys.argv[1:])
