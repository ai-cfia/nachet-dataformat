"""
This module represent the function for the table micronutrient, guaranteed and its children element_compound:

"""


class ElementCreationError(Exception):
    pass


class ElementNotFoundError(Exception):
    pass


class MicronutrientCreationError(Exception):
    pass


class MicronutrientNotFoundError(Exception):
    pass


class GuaranteedCreationError(Exception):
    pass


class GuaranteedNotFoundError(Exception):
    pass


def new_element(cursor, number, name_fr, name_en, symbol):
    """
    This function add a new element in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - number (int): The number of the element.
    - name_fr (str): The name of the element in French.
    - name_en (str): The name of the element in English.
    - symbol (str): The symbol of the element.

    Returns:
    - str: The UUID of the element.
    """

    try:
        query = """
            INSERT INTO element_compound (number,name_fr,name_en,symbol)
            VALUES (%s,%s,%s,%s)
            RETURNING id
            """
        cursor.execute(query, (number, name_fr, name_en, symbol))
        return cursor.fetchone()[0]
    except Exception:
        raise ElementCreationError


def get_element_id_full_search(cursor, name):
    """
    This function get the element in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the element.

    Returns:
    - str: The UUID of the element.
    """

    try:
        query = """
            SELECT id
            FROM element_compound
            WHERE name_fr ILIKE %s OR name_en ILIKE %s OR symbol = %s
            """
        cursor.execute(query, (name, name, name))
        return cursor.fetchone()[0]
    except Exception:
        raise ElementNotFoundError


def get_element_id_name(cursor, name):
    """
    This function get the element in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the element.

    Returns:
    - str: The UUID of the element.
    """

    try:
        query = """
            SELECT 
                id
            FROM 
                element_compound
            WHERE 
                name_fr = %s OR 
                name_en = %s
            """
        cursor.execute(query, (name, name))
        return cursor.fetchone()[0]
    except Exception:
        raise ElementNotFoundError


def get_element_id_symbol(cursor, symbol):
    """
    This function get the element in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - symbol (str): The symbol of the element.

    Returns:
    - str: The UUID of the element.
    """

    try:
        query = """
            SELECT 
                id
            FROM 
                element_compound
            WHERE 
                symbol ILIKE %s
            """
        cursor.execute(query, (symbol,))
        return cursor.fetchone()[0]
    except Exception:
        raise ElementNotFoundError


def new_micronutrient(
    cursor,
    read_name: str,
    value: float,
    unit: str,
    label_id,
    language: str,
    element_id: int,
    edited=False,
):
    """
    This function add a new micronutrient in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - read_name (str): The name of the micronutrient.
    - value (float): The value of the micronutrient.
    - unit (str): The unit of the micronutrient.
    - element_id (int): The element of the micronutrient.
    - label_id (str): The label of the micronutrient.

    Returns:
    - str: The UUID of the micronutrient.
    """

    try:
        if language.lower() not in ["fr", "en"]:
            raise MicronutrientCreationError("Language not supported")
        query = """
            SELECT new_micronutrient(%s, %s, %s, %s, %s,%s,%s);
            """
        cursor.execute(
            query, (read_name, value, unit, label_id, language, edited, element_id)
        )
        return cursor.fetchone()[0]
    except Exception:
        raise MicronutrientCreationError


def get_micronutrient(cursor, micronutrient_id):
    """
    This function get the micronutrient in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - micronutrient_id (str): The UUID of the micronutrient.

    Returns:
    - str: The UUID of the micronutrient.
    """

    try:
        query = """
            SELECT 
                read_name,
                value,
                unit,
                element_id,
                edited,
                language,
                CONCAT(CAST(read_name AS TEXT),' ',value,' ', unit) AS reading
            FROM 
                micronutrient
            WHERE 
                id = %s
            """
        cursor.execute(query, (micronutrient_id,))
        return cursor.fetchone()
    except Exception:
        raise MicronutrientNotFoundError


def get_micronutrient_json(cursor, label_id) -> dict:
    """
    This function get the micronutrient in the database for a specific label.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_id (str): The UUID of the label.

    Returns:
    - micronutrient (dict): The micronutrient.
    """
    try:
        query = """
            SELECT get_micronutrient_json(%s);
            """
        cursor.execute(query, (label_id,))
        data = cursor.fetchone()
        if data is None:
            raise MicronutrientNotFoundError(
                "Error: could not get the micronutrient for label: " + str(label_id)
            )
        return data[0]
    except MicronutrientNotFoundError as e:
        raise e
    except Exception:
        raise MicronutrientNotFoundError


def get_full_micronutrient(cursor, micronutrient_id):
    """
    This function get the micronutrient in the database with the element.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - micronutrient_id (str): The UUID of the micronutrient.

    """

    try:
        query = """
            SELECT 
                m.read_name,
                m.value,
                m.unit,
                ec.name_fr,
                ec.name_en,
                ec.symbol,
                m.edited,
                m.language,
                CONCAT(CAST(m.read_name AS TEXT),' ',m.value,' ', m.unit) AS reading
            FROM 
                micronutrient m
            LEFT JOIN 
                element_compound ec ON m.element_id = ec.id
            WHERE 
                m.id = %s
            """
        cursor.execute(query, (micronutrient_id,))
        return cursor.fetchone()
    except Exception:
        raise MicronutrientNotFoundError


def get_all_micronutrients(cursor, label_id):
    """
    This function get all the micronutrients with the right label_id in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_id (str): The UUID of the label.

    Returns:
    - str: The UUID of the micronutrient.
    """

    try:
        query = """
            SELECT 
                m.id,
                m.read_name,
                m.value,
                m.unit,
                ec.name_fr,
                ec.name_en,
                ec.symbol,
                m.edited,
                m.language,
                CONCAT(CAST(m.read_name AS TEXT),' ',m.value,' ', m.unit) AS reading
            FROM 
                micronutrient m
            LEFT JOIN 
                element_compound ec ON m.element_id = ec.id
            WHERE 
                m.label_id = %s
            """
        cursor.execute(query, (label_id,))
        return cursor.fetchall()
    except Exception:
        raise MicronutrientNotFoundError
