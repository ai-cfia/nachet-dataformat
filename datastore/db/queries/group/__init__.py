
from psycopg import Cursor
from uuid import UUID
from datastore.db.metadata.validator import is_valid_uuid

class GroupCreationError(Exception):
    pass

class GroupNotFoundError(Exception):
    pass

class GroupUserNotFoundError(Exception):
    pass

class GroupAssignmentError(Exception):
    pass

def create_group(cursor : Cursor, name : str, user_id : UUID) -> str:
    """
    This function creates a group in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the group.
    - user_id (str): The UUID of the user creating the group.

    Returns:
    - The UUID of the group.
    """
    try:
        query = """
            INSERT INTO
                groups (name,created_by_id)
            VALUES
                (%s,%s)
            RETURNING id;
            """
        cursor.execute(
            query,
            (name,user_id),
        )
        return cursor.fetchone()[0]
    except Exception as e:
        raise GroupCreationError(f"Error: group {name} not created\n" + str(e))
    
def add_user_to_group(cursor : Cursor, user_id : UUID, group_id : UUID, assigned_by_id :UUID) -> None:
    """
    This function adds a user to a group in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - group_id (str): The UUID of the group.
    """
    try:
        if assigned_by_id is None:
            assigned_by_id = user_id
        query = """
            INSERT INTO  
                user_group (group_id,user_id,assigned_by_id)
            VALUES
                (%s,%s,%s)
            RETURNING id
            """
        cursor.execute(
            query,
            (group_id,user_id,assigned_by_id),
        )
        if cursor.fetchone() is None:
            raise GroupAssignmentError
        else :
            if not is_valid_uuid(group_id):
                raise GroupAssignmentError
    except GroupAssignmentError:
        raise GroupAssignmentError(f"Error: user {user_id} not added to group {group_id}")
    except Exception:
        raise Exception(f"Error: user {user_id} not added to group {group_id}")
    
def remove_user_from_group(cursor : Cursor, user_id : UUID, group_id : str) -> None:
    """
    This function removes a user from a group in the database.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - group_id (str): The UUID of the group.

    Returns:
    - None
    """
    try:
        query = """
            DELETE FROM 
                user_group
            WHERE 
                group_id = %s AND user_id = %s
            """
        cursor.execute(
            query,
            (group_id,user_id),
        )
    except Exception:
        raise Exception(f"Error: user {user_id} not removed from group {group_id}")
    
def delete_group(cursor : Cursor, group_id : UUID) -> None:
    """
    This function deletes a group from the database and all its children user_group.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - group_id (str): The UUID of the group.

    Returns:
    - None
    """
    try:
        query = """
            DELETE FROM 
                groups
            WHERE 
                id = %s
            """
        cursor.execute(
            query,
            (group_id,),
        )
    except Exception:
        raise Exception(f"Error: group {group_id} not deleted")
    
def is_user_in_group(cursor : Cursor, user_id : UUID, group_id : UUID) -> bool:
    """
    This function checks if a user is in a group in the database.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - group_id (str): The UUID of the group.

    Returns:
    - bool: True if the user is in the group, False otherwise.
    """
    try:
        query = """
            SELECT 
                id
            FROM 
                user_group
            WHERE 
                group_id = %s AND user_id = %s
            """
        cursor.execute(
            query,
            (group_id,user_id),
        )
        return cursor.fetchone() is not None
    except Exception:
        raise GroupNotFoundError(f"Error: user {user_id} not found in group {group_id}")
    
def get_group_users(cursor : Cursor, group_id : UUID) -> dict:
    """
    This function retrieves a group from the database.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - group_id (str): The UUID of the group.

    Returns:
    - dict: The group.
    """
    try:
        query = """
            SELECT 
                user_id,
            FROM 
                user_group
            WHERE 
                group_id = %s
            """
        cursor.execute(
            query,
            (group_id,),
        )
        return cursor.fetchall()
    except Exception:
        raise GroupNotFoundError(f"Error: group {group_id} not found")
    
def get_group_by_name(cursor : Cursor, group_name : str) -> dict:
    """
    This function retrieves a group from the database.
    
    Parameters:
    - cursor (cursor): The cursor of the database.
    - group_name (str): The name of the group.

    Returns:
    - dict: The group.
    """
    try:
        query = """
            SELECT 
                id,
                name,
                created_by_id 
            FROM 
                groups
            WHERE 
                name ILIKE %s
            """
        cursor.execute(
            query,
            (group_name,),)
        return cursor.fetchall()
    except Exception:
        raise GroupNotFoundError(f"Error: group {group_name} not found")