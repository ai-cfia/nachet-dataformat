from psycopg import Cursor
from uuid import UUID
from datastore.db.metadata.validator import is_valid_uuid

class ContainerCreationError(Exception):
    pass

class ContainerNotFoundError(Exception):
    pass

class ContainerUserNotFoundError(Exception):
    pass

class ContainerAssignmentError(Exception):
    pass

def create_container(cursor : Cursor, name : str, user_id : UUID, is_public: bool = False, storage_prefix : str = "user") -> UUID:
    """
    This function creates a container in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the container.
    - user_id (str): The UUID of the user creating the container.
    - is_public (bool): Whether the container is public or not.
    - storage_prefix (str): The prefix of the storage.

    Returns:
    - The UUID of the container.
    """
    try:
        query = """
            INSERT INTO
                containers (name,created_by_id,is_public,storage_prefix)
            VALUES
                (%s,%s,%s,%s)
            RETURNING id;
            """
        cursor.execute(
            query,
            (name,user_id,is_public,storage_prefix),
        )
        return cursor.fetchone()[0]
    except Exception as e:
        raise ContainerCreationError(f"Error: container {name} not created\n" + str(e))


def has_user_access_to_container(cursor : Cursor, user_id : UUID, container_id : UUID) -> bool:
    """
    This function checks if a user has access to a container.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - container_id (str): The UUID of the container.

    Returns:
    - True if the user has access to the container, False otherwise.
    """
    try:
        query = """
            SELECT 
                EXISTS(
                    SELECT
                        1
                    FROM
                        container_user
                    WHERE
                        user_id = %s AND container_id = %s);
            """
        cursor.execute(
            query,
            (user_id,container_id),
        )
        return cursor.fetchone() is not None
    except Exception as e:
        raise ContainerUserNotFoundError(f"Error: user {user_id} not found in container {container_id}\n" + str(e))  

def has_user_group_access_to_container(cursor : Cursor, user_id : UUID, container_id : UUID) -> bool:
    """
    This function checks if a user has access to a container through a group.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - container_id (str): The UUID of the container.

    Returns:
    - True if the user has access to the container, False otherwise.
    """
    try:
        query = """
            SELECT 
                EXISTS(
                    SELECT
                        1
                    FROM
                        container_group
                    WHERE
                        group_id IN (
                            SELECT
                                group_id
                            FROM
                                user_group
                            WHERE
                                user_id = %s
                        ) AND container_id = %s);
            """
        cursor.execute(
            query,
            (user_id,container_id),
        )
        return cursor.fetchone() is not None
    except Exception as e:
        raise ContainerUserNotFoundError(f"Error: user {user_id} not found in container {container_id}\n" + str(e))

def add_user_to_container(cursor : Cursor, user_id : UUID, container_id : UUID, assigned_by_id :UUID) -> None:
    """
    This function adds a user to a container in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - container_id (str): The UUID of the container.
    - assigned_by_id (str): The UUID of the user creating the entry.
    """
    try:
        if assigned_by_id is None:
            assigned_by_id = user_id
        query = """
            INSERT INTO  
                container_user (container_id,user_id created_by_id,last_updated_by_id)
            VALUES
                (%s,%s,%s,%s);
            """
        cursor.execute(
            query,
            (container_id,user_id,assigned_by_id,assigned_by_id),
        )
    except Exception as e:
        raise ContainerAssignmentError(f"Error: user {user_id} not added to container {container_id}\n" + str(e))
    
def add_group_to_container(cursor : Cursor, group_id : UUID, container_id : UUID, user_id :UUID) -> None:
    """
    This function adds a group to a container in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - group_id (str): The UUID of the group.
    - container_id (str): The UUID of the container
    - user_id (str): The UUID of the user creating the entry.
    """
    try:
        if assigned_by_id is None:
            assigned_by_id = group_id
        query = """
            INSERT INTO  
                container_group (container_id,group_id,user_id,user_id)
            VALUES
                (%s,%s,%s,%s);
            """
        cursor.execute(
            query,
            (container_id,group_id,assigned_by_id,assigned_by_id),
        )
    except Exception as e:
        raise ContainerAssignmentError(f"Error: group {group_id} not added to container {container_id}\n" + str(e))
    
def get_container(cursor : Cursor,  container_id : UUID):
    """
    This function gets the UUID of a container.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - container_id (str): The UUID of the container.

    Returns:

    """
    try:
        query = """
                SELECT
                c.name,
                c.is_public,
                c.storage_prefix || '-' || c.id as storage_name,
                c.created_by_id,
                array_agg(cu.user_id),
                array_agg(cg.group_id)
            FROM
                container as c
            LEFT JOIN
                container_user as cu
            ON
                c.id = cu.container_id
            LEFT JOIN
                container_group as cg
            ON
                c.id = cg.container_id
            WHERE
                c.id = %s
            GROUP BY
                c.name,
                c.is_public, 
                storage_name, 
                c.created_by_id
            );
            """
        cursor.execute(
            query,
            (container_id,),
        )
        container_id = cursor.fetchone()
        if container_id is None:
            raise ContainerNotFoundError(f"Error: container {container_name} not found")
        return container_id[0]
    except Exception as e:
        raise ContainerNotFoundError(f"Error: container {container_name} not found\n" + str(e))
    
def delete_container(cursor : Cursor, container_id : UUID) -> None:
    """
    This function deletes a container from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - container_id (str): The UUID of the container.
    """
    try:
        query = """
            DELETE FROM
                containers
            WHERE
                id = %s;
            """
        cursor.execute(
            query,
            (container_id,),
        )
    except Exception as e:
        raise ContainerNotFoundError(f"Error: container {container_id} not deleted\n" + str(e))
    
def delete_user_from_container(cursor : Cursor, user_id : UUID, container_id : UUID) -> None:
    """
    This function deletes a user from a container in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.
    - container_id (str): The UUID of the container.
    """
    try:
        query = """
            DELETE FROM
                container_user
            WHERE
                container_id = %s AND user_id = %s;
            """
        cursor.execute(
            query,
            (container_id,user_id),
        )
    except Exception as e:
        raise ContainerUserNotFoundError(f"Error: user {user_id} not removed from container {container_id}\n" + str(e))
    
def delete_group_from_container(cursor : Cursor, group_id : UUID, container_id : UUID) -> None:
    """
    This function deletes a group from a container in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - group_id (str): The UUID of the group.
    - container_id (str): The UUID of the container.
    """
    try:
        query = """
            DELETE FROM
                container_group
            WHERE
                container_id = %s AND group_id = %s;
            """
        cursor.execute(
            query,
            (container_id,group_id),
        )
    except Exception as e:
        raise ContainerAssignmentError(f"Error: group {group_id} not removed from container {container_id}\n" + str(e))
    
def get_user_containers(cursor:Cursor, user_id:UUID):
    """
    This function gets all the containers of a user.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - user_id (str): The UUID of the user.

    Returns:
    - The containers of the user.
    """
    try:
        query = """
            SELECT
                c.id,
                c.name,
                c.is_public,
                c.storage_prefix || '-' || c.id as storage_name,
                c.storage_prefix,
                c.created_by_id
            FROM
                containers as c
            LEFT JOIN
                container_user as cu
            ON
                c.id = cu.container_id
            WHERE
                cu.user_id = %s
            GROUP BY
                c.id,
                c.name,
                c.is_public,
                storage_name,
                c.created_by_id;
            """
        cursor.execute(
            query,
            (user_id,),
        )
        result = cursor.fetchall()
        if result is None:
            return []
        else :
            return result
    except Exception as e:
        raise ContainerNotFoundError(f"Error: containers for user {user_id} not found\n" + str(e))

