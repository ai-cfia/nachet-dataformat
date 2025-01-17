import json
import os

from dotenv import load_dotenv

import datastore.blob.azure_storage_api as azure_storage
import nachet.db.metadata.inference as inference_metadata
import nachet.db.metadata.machine_learning as ml_metadata
import datastore.db.metadata.picture_set as data_picture_set
import datastore.db.metadata.validator as validator
import nachet.db.queries.inference as inference
import nachet.db.queries.machine_learning as machine_learning
import datastore.db.queries.picture as picture
import nachet.db.queries.seed as seed
import datastore.db.queries.user as user
from datastore import (
    BlobUploadError,
    FolderCreationError,
    UserNotOwnerError,
    get_user_container_client,
)

load_dotenv()

NACHET_BLOB_ACCOUNT = os.environ.get("NACHET_BLOB_ACCOUNT")
if NACHET_BLOB_ACCOUNT is None or NACHET_BLOB_ACCOUNT == "":
    raise ValueError("NACHET_BLOB_ACCOUNT is not set")

NACHET_BLOB_KEY = os.environ.get("NACHET_BLOB_KEY")
if NACHET_BLOB_KEY is None or NACHET_BLOB_KEY == "":
    raise ValueError("NACHET_BLOB_KEY is not set")

NACHET_STORAGE_URL = os.environ.get("NACHET_STORAGE_URL")
if NACHET_STORAGE_URL is None or NACHET_STORAGE_URL == "":
    raise ValueError("NACHET_STORAGE_URL is not set")
DEV_USER_EMAIL = os.environ.get("DEV_USER_EMAIL")
if DEV_USER_EMAIL is None or DEV_USER_EMAIL == "":
    # raise ValueError("DEV_USER_EMAIL is not set")
    print("Warning: DEV_USER_EMAIL not set")

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_DB_USER = os.getenv("NACHET_DB_USER")
NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
if NACHET_DB_URL is None or NACHET_DB_URL == "":
    raise ValueError("NACHET_DB_URL is not set")

NACHET_SCHEMA = os.environ.get("NACHET_SCHEMA")
if NACHET_SCHEMA is None or NACHET_SCHEMA == "":
    raise ValueError("NACHET_SCHEMA is not set")


class InferenceCreationError(Exception):
    pass


class InferenceFeedbackError(Exception):
    pass


class MLRetrievalError(Exception):
    pass


async def upload_picture_unknown(
    cursor, user_id, picture_hash, container_client, picture_set_id=None
):
    """
    Upload a picture that we don't know the seed to the user container

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_id (str): The UUID of the user.
    - picture (str): The image to upload.
    - container_client: The container client of the user.
    """
    try:

        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )

        empty_picture = json.dumps([])

        default_picture_set = str(user.get_default_picture_set(cursor, user_id))
        if picture_set_id is None or str(picture_set_id) == default_picture_set:
            picture_set_id = default_picture_set
            folder_name = "General"
        else:
            folder_name = picture.get_picture_set_name(cursor, picture_set_id)
            if folder_name is None:
                folder_name = str(picture_set_id)

        # Create picture instance in DB
        picture_id = picture.new_picture_unknown(
            cursor=cursor,
            picture=empty_picture,
            picture_set_id=picture_set_id,
        )
        # Upload the picture to the Blob Storage
        response = await azure_storage.upload_image(
            container_client, folder_name, str(picture_set_id), picture_hash, str(picture_id)
        )
        # Update the picture metadata in the DB
        data = {
            "link": azure_storage.build_blob_name(folder_name, str(picture_id)),
            "description": "Uploaded through the API",
        }

        if not response:
            raise BlobUploadError("Error uploading the picture")

        picture.update_picture_metadata(cursor, picture_id, json.dumps(data), 0)

        return picture_id
    except BlobUploadError or azure_storage.UploadImageError:
        raise BlobUploadError("Error uploading the picture")
    except Exception as e:
        print(e)
        raise Exception("Datastore Unhandled Error")


async def upload_picture_known(
    cursor,
    user_id,
    picture_hash,
    container_client,
    seed_id,
    picture_set_id=None,
    nb_seeds=None,
    zoom_level=None,
):
    """
    Upload a picture that the seed is known to the user container

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_id (str): The UUID of the user.
    - picture (str): The image to upload.
    - container_client: The container client of the user.
    - seed_id: The UUID of the seed on the image.
    - picture_set_id: The UUID of the picture set where to add the picture.
    - nb_seeds: The number of seeds on the picture.
    - zoom_level: The zoom level of the picture.
    """
    try:

        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )

        empty_picture = json.dumps([])
        # Create picture instance in DB
        if picture_set_id is None:
            picture_set_id = user.get_default_picture_set(cursor, user_id)
        picture_id = picture.new_picture(
            cursor=cursor,
            picture=empty_picture,
            picture_set_id=picture_set_id,
            seed_id=seed_id,
        )
        # Upload the picture to the Blob Storage
        folder_name = picture.get_picture_set_name(cursor, picture_set_id)
        if folder_name is None:
            folder_name = str(picture_set_id)

        response = await azure_storage.upload_image(
            container_client, folder_name, str(picture_set_id), picture_hash, str(picture_id)
        )
        picture_link = (
            container_client.url
            + "/"
            + azure_storage.build_blob_name(folder_name, str(picture_id))
        )
        # Create picture metadata and update DB instance (with link to Azure blob)
        """
        data = picture_metadata.build_picture(
            pic_encoded=picture_hash,
            link=picture_link,
            nb_seeds=nb_seeds,
            zoom=zoom_level,
            description="upload_picture_set script",
        )
        """
        data = {
            "link": picture_link,
            "nb_seeds": nb_seeds,
            "zoom": zoom_level,
            "description": "Uploaded through the API",
        }
        if not response:
            raise BlobUploadError("Error uploading the picture")

        picture.update_picture_metadata(cursor, picture_id, json.dumps(data), 0)

        return picture_id
    except BlobUploadError or azure_storage.UploadImageError:
        raise BlobUploadError("Error uploading the picture")
    except user.UserNotFoundError as e:
        raise e
    except Exception as e:
        print(e)
        raise Exception("Datastore Unhandled Error")


async def upload_pictures(
    cursor,
    user_id,
    picture_set_id,
    container_client,
    pictures,
    seed_name: str,
    seed_id: str,
    zoom_level: float = None,
    nb_seeds: int = None,
):
    """
    Upload an array of pictures that the seed is known to the user container

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_id (str): The UUID of the user.
    - picture (str): The image to upload.
    - container_client: The container client of the user.
    - pictures array: array of images to upload
    - seed_name: The name of the seed on the images.
    - seed_id: The id of the seed on the images.
    - picture_set_id: The UUID of the picture set where to add the pictures.
    - nb_seeds: The number of seeds on the picture.
    - zoom_level: The zoom level of the picture.

    Returns:
        array of the new pictures UUID
    """
    try:
        if not seed_id and not seed_name:
            raise seed.SeedNotFoundError(
                "Error: seed_name and seed_id not found in the new box. We don't know what to do with it and this should not happen."
            )
        if not seed_id and seed_name:
            if seed.is_seed_registered(cursor=cursor, seed_name=seed_name):
                # mistake from the front end, this seed is known in the db
                seed_id = str(seed.get_seed_id(cursor=cursor, seed_name=seed_name))
            else:
                # create the seed
                seed_id = str(seed.new_seed(cursor=cursor, seed_name=seed_name))

        pictures_id = []
        for picture_encoded in pictures:
            id = await upload_picture_known(
                cursor,
                user_id,
                picture_encoded,
                container_client,
                seed_id,
                picture_set_id,
                nb_seeds,
                zoom_level,
            )
            pictures_id.append(id)

        return pictures_id
    except seed.SeedNotFoundError as e:
        raise e
    except user.UserNotFoundError as e:
        raise e
    except Exception:
        raise BlobUploadError("An error occured during the upload of the pictures")


async def register_inference_result(
    cursor,
    user_id: str,
    inference_dict,
    picture_id: str,
    pipeline_id: str,
    type: int = 1,
):
    """
    Register an inference result in the database

    Parameters:
    - cursor: The cursor object to interact with the database.
    - user_id (str): The UUID of the user.
    - inference (str): The inference to register in a dict string (soon to be json loaded).
    - picture_id (str): The UUID of the picture.
    - pipeline_id (str): The UUID of the pipeline.

    Returns:
    - The inference_dict with the inference_id, box_id and top_id added.
    """
    try:
        trimmed_inference = inference_metadata.build_inference_import(inference_dict)

        model_name = inference_dict["models"][0]["name"]
        pipeline_id = machine_learning.get_pipeline_id_from_model_name(
            cursor, model_name
        )
        inference_dict["pipeline_id"] = str(pipeline_id)

        inference_id = inference.new_inference(
            cursor, trimmed_inference, user_id, picture_id, type, pipeline_id
        )
        nb_object = int(inference_dict["totalBoxes"])
        inference_dict["inference_id"] = str(inference_id)

        # loop through the boxes
        for box_index in range(nb_object):
            # TODO: adapt for multiple types of objects
            if type == 1:
                # TODO : adapt for the seed_id in the inference_dict
                top_id = seed.get_seed_id(
                    cursor, inference_dict["boxes"][box_index]["label"]
                )
                inference_dict["boxes"][box_index]["object_type_id"] = 1
            else:
                raise inference.InferenceCreationError("Error: type not recognized")
            box = inference_metadata.build_object_import(
                inference_dict["boxes"][box_index]
            )
            object_inference_id = inference.new_inference_object(
                cursor, inference_id, box, type, False
            )
            inference_dict["boxes"][box_index]["box_id"] = str(object_inference_id)
            # loop through the topN Prediction
            top_score = -1
            if "topN" in inference_dict["boxes"][box_index]:
                for topN in inference_dict["boxes"][box_index]["topN"]:

                    # Retrieve the right seed_id
                    seed_id = seed.get_seed_id(cursor, topN["label"])
                    id = inference.new_seed_object(
                        cursor, seed_id, object_inference_id, topN["score"]
                    )
                    topN["object_id"] = str(id)
                    if topN["score"] > top_score:
                        top_score = topN["score"]
                        top_id = id
            else:
                seed_id = seed.get_seed_id(
                    cursor, inference_dict["boxes"][box_index]["label"]
                )
                top_id = inference.new_seed_object(
                    cursor,
                    seed_id,
                    object_inference_id,
                    inference_dict["boxes"][box_index]["score"],
                )
            inference.set_inference_object_top_id(cursor, object_inference_id, top_id)
            inference_dict["boxes"][box_index]["top_id"] = str(top_id)

        return inference_dict
    except ValueError:
        raise ValueError("The value of 'totalBoxes' is not an integer.")
    except Exception as e:
        print(e.__str__())
        raise Exception("Unhandled Error")


async def new_correction_inference_feedback(cursor, inference_dict, type: int = 1):
    """
    TODO: doc
    """
    try:
        if "inferenceId" in inference_dict.keys():
            inference_id = inference_dict["inferenceId"]
        else:
            raise InferenceFeedbackError(
                "Error: inference_id not found in the given infence_dict"
            )
        if "userId" in inference_dict.keys():
            user_id = inference_dict["userId"]
            if not (user.is_a_user_id(cursor, user_id)):
                raise InferenceFeedbackError(
                    f"Error: user_id {user_id} not found in the database"
                )
        else:
            raise InferenceFeedbackError(
                "Error: user_id not found in the given infence_dict"
            )
        # if infence_dict["totalBoxes"] != len(inference_dict["boxes"] & infence_dict["totalBoxes"] > 0 ):
        #     if len(inference_dict["boxes"]) == 0:
        #         raise InferenceFeedbackError("Error: No boxes found in the given inference_dict")
        #     else if len(inference_dict["boxes"]) > infence_dict["totalBoxes"]:
        #         raise InferenceFeedbackError("Error: There are more boxes than the totalBoxes")
        #     else if len(inference_dict["boxes"]) < infence_dict["totalBoxes"]:
        #         raise InferenceFeedbackError("Error: There are less boxes than the totalBoxes")
        if inference.is_inference_verified(cursor, inference_id):
            raise InferenceFeedbackError(
                f"Error: Inference {inference_id} is already verified"
            )
        for object in inference_dict["boxes"]:
            box_id = object["boxId"]
            seed_name = object["label"]
            seed_id = object["classId"]
            # flag_seed = False
            # flag_box_metadata = False
            valid = False
            box_metadata = object["box"]

            if box_id == "":
                # This is a new box created by the user

                # Check if the seed is known
                if seed_id == "" and seed_name == "":
                    raise InferenceFeedbackError(
                        "Error: seed_name and seed_id not found in the new box. We don't know what to do with it and this should not happen."
                    )
                if seed_id == "":
                    if seed.is_seed_registered(cursor, seed_name):
                        # Mistake from the FE, the seed is known in the database
                        seed_id = seed.get_seed_id(cursor, seed_name)
                    else:
                        # unknown seed
                        seed_id = seed.new_seed(cursor, seed_name)
                # Create the new object
                object_id = inference.new_inference_object(
                    cursor, inference_id, box_metadata, 1, True
                )
                seed_object_id = inference.new_seed_object(
                    cursor, seed_id, object_id, 0
                )
                # Set the verified_id to the seed_object_id
                inference.set_inference_object_verified_id(
                    cursor, object_id, seed_object_id
                )
                valid = True
            else:
                if inference.is_object_verified(cursor, box_id):
                    raise InferenceFeedbackError(
                        f"Error: Object {box_id} is already verified"
                    )
                # This is a box that was created by the pipeline so it should be within the database
                object_db = inference.get_inference_object(cursor, box_id)
                object_metadata = object_db[1]
                object_id = object_db[0]

                # Check if there are difference between the metadata
                if not (
                    inference_metadata.compare_object_metadata(
                        box_metadata, object_metadata["box"]
                    )
                ):
                    # Update the object metadata
                    # flag_box_metadata = True
                    inference.set_object_box_metadata(
                        cursor, box_id, json.dumps(box_metadata)
                    )

                # Check if the seed is known
                if seed_id == "":
                    if seed_name == "":
                        # box has been deleted by the user
                        valid = False
                    else:
                        valid = True
                        if seed.is_seed_registered(cursor, seed_name):
                            # The seed is known in the database and it was a mistake from the FE
                            seed_id = seed.get_seed_id(cursor, seed_name)
                        else:  # The seed is not known in the database
                            seed_id = seed.new_seed(cursor, seed_name)
                            seed_object_id = inference.new_seed_object(
                                cursor, seed_id, object_id, 0
                            )
                            inference.set_inference_object_verified_id(
                                cursor, object_id, seed_object_id
                            )

                # If a seed is selected by the user or if it is a known seed that the FE has not recognized
                if seed_id != "":
                    # Box is still valid
                    valid = True
                    # Check if a new seed has been selected
                    top_inference_id = inference.get_inference_object_top_id(
                        cursor, object_db[0]
                    )
                    new_top_id = inference.get_seed_object_id(cursor, seed_id, box_id)

                    if new_top_id is None:
                        # Seed selected was not an inference guess, we need to create a new seed_object
                        new_top_id = inference.new_seed_object(
                            cursor, seed_id, box_id, 0
                        )
                        inference.set_inference_object_verified_id(
                            cursor, box_id, new_top_id
                        )
                        # flag_seed = True
                    if top_inference_id != new_top_id:
                        # Seed was not correctly identified, set the verified_id to the correct seed_object.id
                        # flag_seed = True
                        inference.set_inference_object_verified_id(
                            cursor, box_id, new_top_id
                        )
                    else:
                        # Seed was correctly identified, set the verified_id to the top_id
                        # flag_seed = False
                        inference.set_inference_object_verified_id(
                            cursor, box_id, top_inference_id
                        )

            # Update the object validity
            inference.set_inference_object_valid(cursor, box_id, valid)
        inference.verify_inference_status(cursor, inference_id, user_id)
    except InferenceFeedbackError:
        raise
    except Exception as e:
        print(e.__str__())
        raise Exception("Datastore Unhandled Error")


async def new_perfect_inference_feeback(cursor, inference_id, user_id, boxes_id):
    """
    Update objects when a perfect feedback is sent by a user and update the inference if all the objects in it are verified.

    Args:
        cursor: The cursor object to interact with the database.
        inference_id (str): id of the inference on which feedback is given
        user_id (str): id of the user giving a feedback
        boxes_id (str array): array of id of the objects that are correctly identified
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if boxes_id exists
        for box_id in boxes_id:
            if not inference.check_inference_object_exist(cursor, box_id):
                raise inference.InferenceObjectNotFoundError(
                    f"Error: could not get inference object for id {box_id}"
                )
        # Check if inference exists
        if not inference.check_inference_exist(cursor, inference_id):
            raise inference.InferenceNotFoundError(
                f"Inference not found based on the given id: {inference_id}"
            )

        if inference.is_inference_verified(cursor, inference_id):
            raise inference.InferenceAlreadyVerifiedError(
                f"Can't add feedback to a verified inference, id: {inference_id}"
            )

        for object_id in boxes_id:
            top_inference_id = inference.get_inference_object_top_id(cursor, object_id)
            inference.set_inference_object_verified_id(
                cursor, object_id, top_inference_id
            )
            inference.set_inference_object_valid(cursor, object_id, True)

        inference.verify_inference_status(cursor, inference_id, user_id)

    except (
        user.UserNotFoundError,
        inference.InferenceObjectNotFoundError,
        inference.InferenceNotFoundError,
        inference.InferenceAlreadyVerifiedError,
    ) as e:
        raise e
    except Exception as e:
        print(e)
        raise Exception(f"Datastore Unhandled Error : {e}")


async def import_ml_structure_from_json_version(cursor, ml_version: dict):
    """
    TODO: build tests
    """
    pipelines = ml_version["pipelines"]
    models = ml_version["models"]
    # Create the models
    for model in models:
        model_db = ml_metadata.build_model_import(model)
        task_id = machine_learning.get_task_id(cursor, model["task"])
        model_name = model["model_name"]
        endpoint_name = model["endpoint_name"]
        model_id = machine_learning.new_model(
            cursor, model_name, endpoint_name, task_id
        )
        # set active_version if not the test model
        if model_name != "test_model1":
            version = "0.0.1"
            model_version_id = machine_learning.new_model_version(
                cursor, model_id, version, model_db
            )
            machine_learning.set_active_model(
                cursor, str(model_id), str(model_version_id)
            )
    # Create the pipelines
    for pipeline in pipelines:
        pipeline_db = ml_metadata.build_pipeline_import(pipeline)
        pipeline_name = pipeline["pipeline_name"]
        model_ids = []
        # Establish the relationship between the pipelines and its models
        for name_model in pipeline["models"]:
            model_id = 0
            model_id = machine_learning.get_model_id_from_name(cursor, name_model)
            if validator.is_valid_uuid(model_id):
                model_ids.append(model_id)
            else:
                raise ValueError(f"Model {name_model} not found")
        pipeline_id = machine_learning.new_pipeline(
            cursor, pipeline_db, pipeline_name, model_ids
        )
        # set the pipeline active if not the test pipeline
        if pipeline_name != "test_pipeline":
            machine_learning.set_active_pipeline(cursor, str(pipeline_id))


async def get_ml_structure(cursor):
    """
    This function retrieves the machine learning structure from the database.

    Returns a usable json object with the machine learning structure for the FE and BE
    """
    try:
        ml_structure = {"pipelines": [], "models": []}
        pipelines = machine_learning.get_active_pipeline(cursor)
        if len(pipelines) == 0:
            raise MLRetrievalError("No Active pipelines found in the database.")
        model_list = []
        for pipeline in pipelines:
            # (id, name, active:bool, is_default: bool, data, model_ids: array)
            pipeline_name = pipeline[1]
            pipeline_id = pipeline[0]
            default = pipeline[3]
            model_ids = pipeline[5]
            pipeline_dict = ml_metadata.build_pipeline_export(
                pipeline[4], pipeline_name, pipeline_id, default, model_ids
            )
            ml_structure["pipelines"].append(pipeline_dict)
            for model_id in model_ids:
                if model_id not in model_list:
                    model_list.append(model_id)
                model_db = machine_learning.get_model(cursor, model_id)
                # (id, name, endpoint_name, task_name, data,version: str)
                model_name = model_db[1]
                model_endpoint = model_db[2]
                model_task = model_db[3]
                model_version = model_db[5]
                model_dict = ml_metadata.build_model_export(
                    model_db[4],
                    model_id,
                    model_name,
                    model_endpoint,
                    model_task,
                    model_version,
                )
                ml_structure["models"].append(model_dict)
        return ml_structure
    except MLRetrievalError:
        raise
    except Exception as e:
        print(e)
        raise Exception("Datastore Unhandled Error")


async def get_seed_info(cursor):
    """
    This function retrieves the seed information from the database.

    Returns a usable json object with the seed information for the FE and BE
    """
    seeds = seed.get_all_seeds(cursor)
    seed_dict = {"seeds": []}
    for seed_db in seeds:
        seed_id = seed_db[0]
        seed_name = seed_db[1]
        seed_dict["seeds"].append({"seed_id": seed_id, "seed_name": seed_name})
    return seed_dict


async def get_picture_sets_info(cursor, user_id: str):
    """This function retrieves the picture sets names and number of pictures from the database.
    This also retrieve for each picture in the picture set their name, if an inference exist and if the picture is validated.

    Args:
        user_id (str): id of the user
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )

        result = []
        picture_sets = picture.get_user_picture_sets(cursor, user_id)
        for picture_set in picture_sets:
            picture_set_info = {}
            picture_set_id = picture_set[0]
            picture_set_name = picture_set[1]

            picture_set_info["picture_set_id"] = str(picture_set_id)
            picture_set_info["folder_name"] = picture_set_name

            pictures = picture.get_picture_set_pictures(cursor, picture_set_id)
            picture_set_info["nb_pictures"] = len(pictures)

            picture_set_info["pictures"] = []
            for pic in pictures:
                picture_info = {}
                picture_id = pic[0]
                picture_info["picture_id"] = str(picture_id)

                is_validated = picture.is_picture_validated(cursor, picture_id)
                inference_exist = picture.check_picture_inference_exist(
                    cursor, picture_id
                )
                picture_info["is_validated"] = is_validated
                picture_info["inference_exist"] = inference_exist

                picture_set_info["pictures"].append(picture_info)
            result.append(picture_set_info)
        return result
    except (
        user.UserNotFoundError,
        picture.GetPictureSetError,
        picture.GetPictureError,
    ) as e:
        raise e
    except Exception as e:
        raise picture.GetPictureSetError(
            f"An error occured while retrieving the picture sets : {e}"
        )


async def get_picture_inference(
    cursor, user_id: str, picture_id: str = None, inference_id: str = None
):
    """
    Retrieves inference (if exist) of the given picture

    Args:
        cursor: The cursor object to interact with the database.
        user_id (str): id of the user
        picture_id (str): id of the picture
        inference_id (str): id of the inference
    """
    try:
        # Si aucun id (ni picture_id ni inference_id) n'est fourni, lève une exception.
        if picture_id is None and inference_id is None:
            raise ValueError("Error: picture_id or inference_id must be provided")

        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )

        # Si picture_id n'est pas fourni, mais inference_id l'est, récupère le picture_id en utilisant inference_id.
        if picture_id is None and inference_id is not None:
            picture_id = str(inference.get_inference_picture_id(cursor, inference_id))

        # Check if picture set exists
        if not picture.is_a_picture_id(cursor, picture_id):
            raise picture.PictureNotFoundError(
                f"Picture not found based on the given id: {picture_id}"
            )
        # Check user is owner of the picture set where the picutre is
        picture_set_id = picture.get_picture_picture_set_id(cursor, picture_id)
        if str(picture.get_picture_set_owner_id(cursor, picture_set_id)) != user_id:
            raise UserNotOwnerError(
                f"User can't access this picture, user uuid :{user_id}, picture : {picture_id}"
            )

        if picture.check_picture_inference_exist(cursor, picture_id):
            inf = inference.get_inference_by_picture_id(cursor, picture_id)

            inf = inference_metadata.rebuild_inference(cursor, inf)

            return inf
        else:
            return None

    except (
        user.UserNotFoundError,
        picture.PictureNotFoundError,
        UserNotOwnerError,
        ValueError,
    ) as e:
        raise e
    except Exception as e:
        raise Exception(f"Datastore Unhandled Error : {e}")


async def get_picture_blob(cursor, user_id: str, container_client, picture_id: str):
    """
    Retrieves blob of the given picture

    Args:
        cursor: The cursor object to interact with the database.
        user_id (str): id of the user
        picture_id (str): id of the picture set
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_id(cursor, picture_id):
            raise picture.PictureNotFoundError(
                f"Picture set not found based on the given id: {picture_id}"
            )
        # Check user is owner of the picture set where the picutre is
        picture_set_id = picture.get_picture_picture_set_id(cursor, picture_id)
        if str(picture.get_picture_set_owner_id(cursor, picture_set_id)) != user_id:
            raise UserNotOwnerError(
                f"User can't access this picture, user uuid :{user_id}, picture : {picture_id}"
            )
        if str(user.get_default_picture_set(cursor, user_id)) == str(picture_set_id):
            folder_name = "General"
        else:
            folder_name = picture.get_picture_set_name(cursor, picture_set_id)
        blob_name = azure_storage.build_blob_name(folder_name, str(picture_id))
        picture_blob = await azure_storage.get_blob(container_client, blob_name)
        return picture_blob
    except (
        user.UserNotFoundError,
        picture.PictureNotFoundError,
        UserNotOwnerError,
    ) as e:
        raise e


async def delete_picture_set_with_archive(
    cursor, user_id, picture_set_id, container_client
):
    """
    Delete a picture set from the database and the blob storage but archives inferences and pictures in dev container

    Args:
        cursor: The cursor object to interact with the database.
        user_id (str): id of the user
        picture_set_id (str): id of the picture set to delete
        container_client: The container client of the user.
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_set_id(cursor, picture_set_id):
            raise picture.PictureSetNotFoundError(
                f"Picture set not found based on the given id: {picture_set_id}"
            )
        # Check user is owner of the picture set
        if picture.get_picture_set_owner_id(cursor, picture_set_id) != user_id:
            raise UserNotOwnerError(
                f"User can't delete this folder, user uuid :{user_id}, folder name : {picture_set_id}"
            )
        # Check if the picture set is the default picture set
        general_folder_id = str(user.get_default_picture_set(cursor, user_id))
        if general_folder_id == picture_set_id:
            raise picture.PictureSetDeleteError(
                f"User can't delete the default picture set, user uuid :{user_id}"
            )

        folder_name = picture.get_picture_set_name(cursor, picture_set_id)
        if folder_name is None:
            folder_name = str(picture_set_id)
        validated_pictures = picture.get_validated_pictures(cursor, picture_set_id)

        dev_user_id = user.get_user_id(cursor, DEV_USER_EMAIL)
        dev_container_client = await get_user_container_client(
            dev_user_id, NACHET_STORAGE_URL, NACHET_BLOB_ACCOUNT, NACHET_BLOB_KEY
        )
        if not dev_container_client.exists():
            raise BlobUploadError(
                f"Error while connecting to the dev container: {dev_user_id}"
            )
        if not await azure_storage.is_a_folder(dev_container_client, str(user_id)):
            await azure_storage.create_folder(dev_container_client, str(user_id))

        picture_set = data_picture_set.build_picture_set_metadata(
            dev_user_id, len(validated_pictures)
        )
        dev_picture_set_id = picture.new_picture_set(
            cursor=cursor,
            picture_set_metadata=picture_set,
            user_id=dev_user_id,
            folder_name=folder_name,
        )

        folder_created = await azure_storage.create_dev_container_folder(
            dev_container_client, str(picture_set_id), folder_name, str(user_id)
        )
        if not folder_created:
            raise FolderCreationError(
                f"Error while creating this folder : {picture_set_id}"
            )

        for picture_id in picture.get_validated_pictures(cursor, picture_set_id):
            picture_metadata = picture.get_picture(cursor, picture_id)
            # change the link in the metadata
            blob_name = azure_storage.build_blob_name(folder_name, str(picture_id))
            # special case for the dev container pictures
            dev_blob_name = azure_storage.build_blob_name(
                folder_path=user_id, blob_name=blob_name
            )
            picture_metadata["link"] = dev_blob_name
            picture.update_picture_metadata(
                cursor, picture_id, json.dumps(picture_metadata), 0
            )
            # set picture set to dev one
            picture.update_picture_picture_set_id(
                cursor, picture_id, dev_picture_set_id
            )
            # move the picture to the dev container
            if not (
                await azure_storage.move_blob(
                    blob_name,
                    dev_blob_name,
                    str(dev_picture_set_id),
                    container_client,
                    dev_container_client,
                )
            ):
                raise BlobUploadError(
                    f"Error while moving the picture : {picture_id} to the dev container"
                )

        if len(picture.get_validated_pictures(cursor, picture_set_id)) > 0:
            raise picture.PictureSetDeleteError(
                f"Can't delete the folder, there are still validated pictures in it, folder name : {picture_set_id}"
            )

        # Delete the folder in the blob storage
        await azure_storage.delete_folder(container_client, str(picture_set_id))
        # Delete the picture set
        picture.delete_picture_set(cursor, picture_set_id)

        return dev_picture_set_id
    except (
        user.UserNotFoundError,
        picture.PictureSetNotFoundError,
        picture.PictureSetDeleteError,
        UserNotOwnerError,
    ) as e:
        raise e
    except Exception as e:
        print(f"Datastore Unhandled Error : {e}")
        raise Exception("Datastore Unhandled Error")


async def find_validated_pictures(cursor, user_id, picture_set_id):
    """
    Find pictures that have been validated by the user in the given picture set

    Args:
        cursor: The cursor object to interact with the database.
        user_id (str): id of the user that should be the owner of the picture set
        picture_set_id (str): id of the picture set

    Returns:
        list of picture_id
    """
    try:
        # Check if user exists
        if not user.is_a_user_id(cursor=cursor, user_id=user_id):
            raise user.UserNotFoundError(
                f"User not found based on the given id: {user_id}"
            )
        # Check if picture set exists
        if not picture.is_a_picture_set_id(cursor, picture_set_id):
            raise picture.PictureSetNotFoundError(
                f"Picture set not found based on the given id: {picture_set_id}"
            )
        # Check user is owner of the picture set
        if picture.get_picture_set_owner_id(cursor, picture_set_id) != user_id:
            raise UserNotOwnerError(
                f"User isn't owner of this folder, user uuid :{user_id}, folder uuid : {picture_set_id}"
            )

        validated_pictures_id = picture.get_validated_pictures(cursor, picture_set_id)
        return validated_pictures_id
    except (
        user.UserNotFoundError,
        picture.PictureSetNotFoundError,
        UserNotOwnerError,
    ) as e:
        raise e
    except Exception as e:
        print(e)
        raise Exception("Datastore Unhandled Error")
