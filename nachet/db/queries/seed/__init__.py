"""
This file contains the queries for the seed table.
"""


class SeedNotFoundError(Exception):
    pass


class SeedCreationError(Exception):
    pass


def get_all_seeds_names(cursor):
    """
    This function returns all the seed name from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.

    Returns:
    - list of all the names.
    """
    try:
        query = """
            SELECT 
                name 
            FROM 
                seed
            """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception:
        raise Exception("Error: seeds could not be retrieved")
    
def get_all_seeds(cursor):
    """
    This function returns all the seed from the database.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    
    Returns:
    - list of tuple (id,seed_name)
    """
    try:
        query = """
            SELECT 
                id,name 
            FROM 
                seed
            """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception:
        raise Exception("Error: seeds could not be retrieved")    
    
def format_seed_name(seed_name: str) -> str:
    """
    This function formats the seed name.

    Parameters:
    - seed_name (str): Name of the seed

    Returns:
    - The formatted seed name.
    """

    valid = False
    current_name = seed_name
    while (not valid) & (current_name != ""):
        current_name = current_name.strip()
        if current_name[0].isdigit():
            current_name = current_name[1:]
        else:
            valid = True
    # Check if initial character is a number
    return current_name


def get_seed_id(cursor, seed_name: str) -> str:
    """
    This function retrieve the UUUID of a seed.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_name (str): Name of the seed

    Returns:
    - The UUID of the seed.
    """
    try:
        seed_name = format_seed_name(seed_name)
        query = """
            SELECT 
                id 
            FROM 
                seed
            WHERE 
                name ILIKE %s
                """
        seed_name= "%"+seed_name
        cursor.execute(query, (seed_name,))
        result = cursor.fetchone()[0]
        return result
    except TypeError:
        raise SeedNotFoundError(f"Error: seed {seed_name} not found")
    except Exception:
        raise Exception("unhandled error")

def get_seed_name(cursor, seed_id:str) -> str :
    """
    This function retrieves the name of a seed from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_id (str): The id of the seed.

    Returns:
    - The name of the seed.
    """
    try:
        query = """
            SELECT 
                name 
            FROM 
                seed
            WHERE 
                id = %s
            """
        cursor.execute(query, (seed_id,))
        return cursor.fetchone()[0]
    except TypeError:
        raise SeedNotFoundError("Error: seed not found")
    except Exception:
        raise Exception("unhandled error")

def new_seed(cursor, seed_name: str):
    """
    This function inserts a new seed into the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_name (str): Name of the seed

    """
    try:
        query = """
            INSERT INTO 
                seed(name)
            VALUES
                (%s)
            RETURNING id
            """
        cursor.execute(
            query,
            (seed_name,),
        )
        return cursor.fetchone()[0]
    except Exception:
        raise SeedCreationError("Error: picture_set not uploaded")


def is_seed_registered(cursor, seed_name: str) -> bool:
    """
    This function checks if a seed is registered in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_name (str): Name of the seed

    Returns:
    - True if the seed is registered in the database, False otherwise.
    """
    try:
        query = """
            SELECT EXISTS(
                SELECT 
                    1 
                FROM 
                    seed
                WHERE 
                    name = %s
            )
                """
        cursor.execute(query, (seed_name,))
        res = cursor.fetchone()[0]
        return res
    except Exception:
        raise Exception("Error: could not check if seed name is a seed")

def get_seed_object_seed_id(cursor, seed_object_id: str) -> str:
    """
    This function retrieves the seed_id of a seed object.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - seed_object_id (str): The id of the seed object.

    Returns:
    - The seed_id of the seed object.
    """
    try:
        query = """
            SELECT 
                seed_id 
            FROM 
                seed_obj
            WHERE 
                id = %s
            """
        cursor.execute(query, (seed_object_id,))
        return cursor.fetchone()[0]
    except TypeError:
        raise SeedNotFoundError("Error: seed not found")
    except Exception:
        raise Exception("unhandled error")
