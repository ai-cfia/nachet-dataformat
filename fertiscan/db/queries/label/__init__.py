"""
This module represent the function for the table label_information
"""

from uuid import UUID

from psycopg import Cursor
from psycopg.rows import dict_row
from psycopg.sql import SQL


class LabelInformationNotFoundError(Exception):
    pass


def new_label_information(
    cursor,
    name: str,
    lot_number: str,
    npk: str,
    registration_number: str,
    n: float,
    p: float,
    k: float,
    title_en: str,
    title_fr: str,
    is_minimal: bool,
    company_info_id,
    manufacturer_info_id,
):
    """
    This function create a new label_information in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - lot_number (str): The lot number of the label_information.
    - npk (str): The npk of the label_information.
    - registration_number (str): The registration number of the label_information.
    - n (float): The n of the label_information.
    - p (float): The p of the label_information.
    - k (float): The k of the label_information.
    - title_en (str): The english title of the guaranteed analysis.
    - title_fr (str): The french title of the guaranteed analysis.
    - is_minimal (bool): if the tital is minimal for the guaranteed analysis.
    - company_info_id (str): The UUID of the company.
    - manufacturer_info_id (str): The UUID of the manufacturer.

    Returns:
    - str: The UUID of the label_information
    """
    try:
        query = """
        SELECT new_label_information(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
        cursor.execute(
            query,
            (
                name,
                lot_number,
                npk,
                registration_number,
                n,
                p,
                k,
                title_en,
                title_fr,
                is_minimal,
                company_info_id,
                manufacturer_info_id,
            ),
        )
        return cursor.fetchone()[0]
    except Exception as e:
        raise e


def new_label_information_complete(
    cursor, lot_number, npk, registration_number, n, p, k, weight, density, volume
):
    ##TODO: Implement this function
    return None


def get_label_information(cursor, label_information_id):
    """
    This function get a label_information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_information_id (str): The UUID of the label_information.

    Returns:
    - dict: The label_information
    """
    try:
        query = """
            SELECT 
                id,
                product_name,
                lot_number, 
                npk, 
                registration_number, 
                n, 
                p, 
                k, 
                guaranteed_title_en,
                guaranteed_title_fr,
                title_is_minimal,
                company_info_id,
                manufacturer_info_id
            FROM 
                label_information
            WHERE 
                id = %s
            """
        cursor.execute(query, (label_information_id,))
        return cursor.fetchone()
    except Exception as e:
        raise e


def get_label_information_json(cursor, label_info_id) -> dict:
    """
    This function retrieves the label information from the database in json format.

    Parameters:
    - cursor (cursor): The cursor object to interact with the database.
    - label_info_id (str): The label information id.

    Returns:
    - dict: The label information in json format.
    """
    try:
        query = """
            SELECT get_label_info_json(%s);
            """
        cursor.execute(query, (str(label_info_id),))
        label_info = cursor.fetchone()
        if label_info is None or label_info[0] is None:
            raise LabelInformationNotFoundError(
                "Error: could not get the label information: " + str(label_info_id)
            )
        return label_info[0]
    except LabelInformationNotFoundError as e:
        raise e
    except Exception as e:
        raise e


def get_label_dimension(cursor, label_id):
    """
    This function get the label_dimension from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_id (str): The UUID of the label.

    Returns:
    - dict: The label_dimension
    """
    try:
        query = """
            SELECT 
                "label_id",
                "company_info_id",
                "company_location_id",
                "manufacturer_info_id",
                "manufacturer_location_id",
                "instructions_ids",
                "cautions_ids",
                "first_aid_ids",
                "warranties_ids",
                "specification_ids",
                "ingredient_ids",
                "micronutrient_ids",
                "guaranteed_ids",
                "weight_ids",
                "volume_ids",
                "density_ids"
            FROM 
                label_dimension
            WHERE 
                label_id = %s;
            """
        cursor.execute(query, (label_id,))
        data = cursor.fetchone()
        if data is None or data[0] is None:
            raise LabelInformationNotFoundError(
                "Error: could not get the label dimension for label: " + str(label_id)
            )
        return data
    except Exception as e:
        raise e


def get_company_manufacturer_json(cursor: Cursor, label_id: str | UUID):
    """ """
    query = SQL(
        "SELECT * FROM label_company_manufacturer_json_view WHERE label_id = %s;"
    )
    with cursor.connection.cursor(row_factory=dict_row) as new_cur:
        new_cur.execute(query, (label_id,))
        return new_cur.fetchone()
