"""
This module represent the function for the table label_information
"""

from psycopg import Cursor

from fertiscan.db.queries.errors import (
    LabelDimensionNotFoundError,
    LabelDimensionQueryError,
    LabelInformationCreationError,
    LabelInformationNotFoundError,
    LabelInformationRetrievalError,
    handle_query_errors,
)


@handle_query_errors(LabelInformationCreationError)
def new_label_information(
    cursor,
    name: str,
    lot_number: str,
    npk: str,
    n: float,
    p: float,
    k: float,
    title_en: str,
    title_fr: str,
    is_minimal: bool,
    record_keeping: bool,
):
    """
    This function create a new label_information in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - lot_number (str): The lot number of the label_information.
    - npk (str): The npk of the label_information.
    - n (float): The n of the label_information.
    - p (float): The p of the label_information.
    - k (float): The k of the label_information.
    - title_en (str): The english title of the guaranteed analysis.
    - title_fr (str): The french title of the guaranteed analysis.
    - is_minimal (bool): if the tital is minimal for the guaranteed analysis.
    - record_keeping (bool): if the label is a record keeping.

    Returns:
    - str: The UUID of the label_information
    """
    query = """
    SELECT new_label_information(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
    cursor.execute(
        query,
        (
            name,
            lot_number,
            npk,
            n,
            p,
            k,
            title_en,
            title_fr,
            is_minimal,
            record_keeping,
        ),
    )
    if result := cursor.fetchone():
        return result[0]
    raise LabelInformationCreationError(
        "Failed to create label information. No data returned."
    )


def new_label_information_complete(
    cursor, lot_number, npk, registration_number, n, p, k, weight, density, volume
):
    ##TODO: Implement this function
    return None


@handle_query_errors(LabelInformationRetrievalError)
def get_label_information(cursor: Cursor, label_information_id: str) -> dict:
    """
    This function get a label_information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_information_id (str): The UUID of the label_information.

    Returns:
    - dict: A dictionary containing the label information.

    Raises:
    - InspectionRetrievalError: Custom error for handling retrieval issues.
    """
    query = """
        SELECT 
            id,
            product_name,
            lot_number, 
            npk, 
            n, 
            p, 
            k, 
            guaranteed_title_en,
            guaranteed_title_fr,
            title_is_minimal,
            record_keeping
        FROM 
            label_information
        WHERE 
            id = %s
        """
    cursor.execute(query, (label_information_id,))
    return cursor.fetchone()


@handle_query_errors(LabelInformationRetrievalError)
def get_label_information_json(cursor, label_info_id) -> dict:
    """
    This function retrieves the label information from the database in json format.

    Parameters:
    - cursor (cursor): The cursor object to interact with the database.
    - label_info_id (str): The label information id.

    Returns:
    - dict: The label information in json format.
    """
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


@handle_query_errors(LabelDimensionQueryError)
def get_label_dimension(cursor, label_id):
    """
    This function get the label_dimension from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_id (str): The UUID of the label.

    Returns:
    - dict: The label_dimension
    """
    query = """
        SELECT 
            "label_id",
            "organization_info_ids",
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
        raise LabelDimensionNotFoundError(
            "Error: could not get the label dimension for label: " + str(label_id)
        )
    return data


def delete_label_info(cursor: Cursor, label_id: str):
    """
    This function deletes a label information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - label_id (str): The UUID of the label information.

    Returns:
    - int: The number of rows affected by the query. (should be at least one)
    """
    query = """
    DELETE FROM label_information WHERE id = %s;
    """
    cursor.execute(query, (label_id,))
    return cursor.rowcount
