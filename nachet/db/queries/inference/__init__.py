"""
This module contains the queries related to the inference related tables.

"""

class InferenceCreationError(Exception):
    pass

class SeedObjectCreationError(Exception):  
    pass

class InferenceNotFoundError(Exception):
    pass

class InferenceObjectNotFoundError(Exception):
    pass

class InferenceAlreadyVerifiedError(Exception):
    pass

"""

INFERENCE TABLE QUERIES

"""

def new_inference(cursor, inference, user_id: str, picture_id:str,type, pipeline_id:str):
    """
    This function uploads a new inference to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference (str): The inference to upload. Must be formatted as a json
    - user_id (str): The UUID of the user uploading.
    - picture_id (str): The UUID of the picture the inference is related to.

    Returns:
    - The inference dict with the UUIDs of the inference, boxes and topN.
    """
    try:
        query = """
            INSERT INTO 
                inference(
                    inference,
                    picture_id,
                    user_id,
                    pipeline_id
                    )
            VALUES
                (%s,%s,%s,%s)
            RETURNING id    
            """
        cursor.execute(
            query,
            (
                inference,
                picture_id,
                user_id,
                pipeline_id,
            ),
        )
        inference_id=cursor.fetchone()[0]
        return inference_id
    except Exception as e:
        raise InferenceCreationError("Error: inference not uploaded " + str(e))

def get_inference(cursor, inference_id: str):
    """
    This function gets an inference from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.

    Returns:
    - The inference.
    """
    try:
        query = """
            SELECT 
                inference
            FROM 
                inference
            WHERE 
                id = %s
            """
        cursor.execute(query, (inference_id,))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise InferenceNotFoundError(f"Error: could not get inference {inference_id}")
    
def get_inference_picture_id(cursor, inference_id: str):
    """
    This functions retrieve picture_id of a given inference
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.
    """
    try :
        query = """
            SELECT 
                picture_id
            FROM 
                inference
            WHERE 
                id = %s
            """
        cursor.execute(query, (inference_id,))
        result = cursor.fetchone()[0]
        return result
    except Exception:
        raise InferenceNotFoundError(
            f"Error: could not get picture_id for the inference {inference_id}")
    
def get_inference_by_picture_id(cursor, picture_id: str):
    """
    This functions retrieve inference of a given picture
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - picture_id (str): The UUID of the picture.
    """
    try :
        query = """
            SELECT 
                id, inference, pipeline_id
            FROM 
                inference
            WHERE 
                picture_id = %s
            """
        cursor.execute(query, (picture_id,))
        result = cursor.fetchone()
        return result
    except Exception:
        raise InferenceNotFoundError(
            f"Error: could not get inference for the picture {picture_id}")

def set_inference_feedback_user_id(cursor, inference_id, user_id):
    """
    This function sets the feedback_user_id of an inference.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.
    - user_id (str): The UUID of the user.
    """
    try:
        query = """
            UPDATE 
                inference
            SET
                feedback_user_id = %s
            WHERE 
                id = %s
            """
        cursor.execute(query, (user_id,inference_id))
    except Exception as e:
        print(e)
        raise Exception(f"Error: could not set feedback_user_id {user_id} for inference {inference_id}")
    

def set_inference_verified(cursor, inference_id, is_verified):
    """
    This function sets the inference as verified or not.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.
    - is_verified (bool): is the inference verified.
    """
    try:
        query = """
            UPDATE 
                inference
            SET
                verified = %s
            WHERE 
                id = %s
            """
        cursor.execute(query, (is_verified,inference_id))
    except Exception:
        raise Exception(f"Error: could not update verified {is_verified} for inference {inference_id}")
    
def is_inference_verified(cursor, inference_id):
    """
    Check if an inference is verified or not.
    
    return True if verified, False otherwise
    """
    try:
        query = """
            SELECT 
                verified
            FROM
                inference
            WHERE 
                id = %s
            """
        cursor.execute(query, (str(inference_id),))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception(f"Error: could not select verified column for inference {inference_id}")

def is_object_verified(cursor, object_id):
    """
    Check if an object is verified or not.
    
    return True if verified, False otherwise
    """
    try:
        query = """
            SELECT 
                verified_id
            FROM
                object
            WHERE 
                id = %s
            """
        cursor.execute(query, (str(object_id),))
        res = cursor.fetchone()[0]
        return (res is not None)
    except ValueError:
        return False
    except Exception:
        raise Exception(f"Error: could not select verified_id column for object {object_id}")

def get_inference_object_verified_id(cursor, object_id):
    """
    Check if an object is verified or not.
    
    return True if verified, False otherwise
    """
    try:
        query = """
            SELECT 
                verified_id
            FROM
                object
            WHERE 
                id = %s
            """
        cursor.execute(query, (str(object_id),))
        return cursor.fetchone()[0] 
    except ValueError as e:
        return e
    except Exception:
        raise Exception(f"Error: could not get verified_id column for object {object_id}")

def verify_inference_status(cursor, inference_id, user_id):
    """
    Set inference verified if inference is fully verified and set the user as the feedback user
    """
    objects = get_objects_by_inference(cursor, inference_id)
    if all(obj[4] is not None for obj in objects) :
        set_inference_feedback_user_id(cursor, inference_id, user_id)
        set_inference_verified(cursor, inference_id, True)

def check_inference_exist(cursor, inference_id):
    """
    Check if an inference exists in the database.
    
    return True if exists, False otherwise
    """
    try:
        query = """
            SELECT 
                id
            FROM
                inference
            WHERE 
                id = %s
            """
        cursor.execute(query, (str(inference_id),))
        res = cursor.fetchone()
        return res is not None
    except Exception:
        raise Exception(f"Error: could not check if inference {inference_id} exists")
    
"""

OBJECT TABLE QUERIES

"""

def new_inference_object(cursor, inference_id: str,box_metadata:str,type_id:int,manual_detection:bool=False):
    """
    This function uploads a new inference object to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.
    - type_id (int): The UUID of the type.

    Returns:
    - The UUID of the inference object.
    """
    try:
        query = """
            INSERT INTO 
                object(
                    inference_id,
                    box_metadata,
                    type_id,
                    manual_detection
                    )
            VALUES
                (%s,%s,%s,%s)
            RETURNING id    
            """
        cursor.execute(
            query,
            (
                inference_id,
                box_metadata,
                type_id,
                manual_detection,
            ),
        )
        return cursor.fetchone()[0]
    except Exception:
        raise InferenceCreationError("Error: inference object not uploaded")

def get_inference_object(cursor, inference_object_id: str):
    """
        This function gets an object from the database.

        Parameters:
        - cursor (cursor): The cursor of the database.
        - inference_object_id (str): The UUID of the object.

        Returns:
        - The object.
    """
    try:
        query = """
            SELECT 
                id,
                box_metadata,
                inference_id,
                type_id,
                verified_id,
                top_id,
                valid,
                top_id,
                upload_date,
                updated_at
            FROM 
                object
            WHERE 
                id = %s
            """
        cursor.execute(query, (inference_object_id,))
        res = cursor.fetchone()
        if res is None:
            raise Exception(f"Error: could not find inference object for id {inference_object_id}")
        return res
    except Exception:
        raise InferenceObjectNotFoundError(f"Error: could not get inference object for id {inference_object_id}")

def get_objects_by_inference(cursor, inference_id: str):
    """
    This function gets all objects from the database related to an inference.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.

    Returns:
    - The objects.
    """
    try:
        query = """
            SELECT 
                *
            FROM 
                object
            WHERE 
                inference_id = %s
            """
        cursor.execute(query, (inference_id,))
        res = cursor.fetchall()
        if res is None:
            raise Exception(f"Error: could not find objects for inference {inference_id}")
        return res
    except Exception:
        raise InferenceObjectNotFoundError(f"Error: could not get objects for inference {inference_id}")

def set_inference_object_top_id(cursor, inference_object_id: str, top_id:str):
    """
    This function sets the top_id of an inference.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.
    - top_id (str): The UUID of the top.
    """
    try:
        query = """
            UPDATE 
                object
            SET
                top_id = %s,
                updated_at = now()
            WHERE 
                id = %s
            """
        cursor.execute(query, (top_id,inference_object_id))
    except Exception as e:
        raise Exception(f"Error: could not set top_id {top_id} for inference {inference_object_id}" + str(e))
    
def get_inference_object_top_id(cursor, inference_object_id: str):
    """
    This function gets the top_id of an inference.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_id (str): The UUID of the inference.

    Returns:
    - The UUID of the top.
    """
    try:
        query = """
            SELECT 
                top_id
            FROM 
                object
            WHERE 
                id = %s
            """
        cursor.execute(query, (inference_object_id,))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception(f"Error: could not get top_inference_id for inference {inference_object_id}")


def set_inference_object_verified_id(cursor, inference_object_id: str, verified_id:str):
    """
    This function sets the verified_id of an object.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_object_id (str): The UUID of the object.
    - verified_id (str): The UUID of the verified.
    """
    try:
        query = """
            UPDATE 
                object
            SET
                verified_id = %s
            WHERE 
                id = %s
            """
        cursor.execute(query, (verified_id,inference_object_id))
    except Exception:
        raise Exception(f"Error: could not update verified_id for object {inference_object_id}")
    
def set_inference_object_valid(cursor, inference_object_id: str, is_valid:bool):
    """
    This function sets the is_valid of an object.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - inference_object_id (str): The UUID of the object.
    - is_valid (bool): if the inference object is valid
    """
    try:
        query = """
            UPDATE 
                object
            SET
                valid = %s
            WHERE 
                id = %s
            """
        cursor.execute(query, (is_valid,inference_object_id))
    except Exception:
        raise Exception(f"Error: could not update valid for object {inference_object_id}")

def check_inference_object_exist(cursor, inference_object_id):
    """
    Check if an inference object exists in the database.
    
    return True if exists, False otherwise
    """
    try:
        query = """
            SELECT 
                EXISTS (
                    SELECT 1 
                    FROM object 
                    WHERE id = %s
                )
            """
        cursor.execute(query, (str(inference_object_id),))
        res = cursor.fetchone()
        return res[0]
    except Exception:
        raise Exception(f"Error: could not check if inference object {inference_object_id} exists")

"""

SEED OBJECT TABLE QUERIES

"""

def new_seed_object(cursor, seed_id: str, object_id:str,score:float):
    """
    This function uploads a new seed object (seed prediction) to the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_id (str): The UUID of the seed.
    - object_id (str): The UUID of the object.
    - score (float): The score of the prediction.

    Returns:
    - The UUID of the seed object.
    """
    try:
        query = """
            INSERT INTO 
                seed_obj(
                    seed_id,
                    object_id,
                    score
                    )
            VALUES
                (%s,%s,%s)
            RETURNING id    
            """
        cursor.execute(
            query,
            (
                seed_id,
                object_id,
                score,
            ),
        )
        return cursor.fetchone()[0]
    except Exception:
        raise SeedObjectCreationError("Error: seed object not uploaded")


def set_object_box_metadata(cursor,object_id:str, metadata:str):
    """
    This function sets the metadata of an object.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - object_id (str): The UUID of the object.
    - metadata (str): The metadata to set.
    """
    try:
        query = """
            UPDATE 
                object
            SET
                box_metadata = %s
            WHERE 
                id = %s
            """
        cursor.execute(query, (metadata,object_id))
    except Exception:
        raise Exception(f"Error: could not set metadata {metadata} for object {object_id}")

def get_seed_object_id(cursor, seed_id: str, object_id:str):
    """
    This function gets the seed object from the feedback table.
    """
    try:
        query = """
            SELECT 
                so.id 
            FROM
                seed_obj so 
            WHERE 
                so.seed_id = %s
            AND 
                so.object_id = %s
            """
        cursor.execute(query, (seed_id,object_id))
        if cursor.rowcount == 0:
            return None
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception(f"Error: could not get seed_object_id for seed_id {seed_id} for object {object_id}")

def get_seed_object_by_object_id(cursor, object_id: str):
    try:
        query = """
            SELECT 
                so.id,
                so.seed_id,
                so.score
            FROM
                seed_obj so 
            WHERE 
                so.object_id = %s
            """
        cursor.execute(query, (object_id,))
        res = cursor.fetchall()
        return res
    except Exception:
        raise Exception(f"Error: could not get seed_object for object {object_id}")
