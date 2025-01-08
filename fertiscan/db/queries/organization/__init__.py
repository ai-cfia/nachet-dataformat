"""
This module represent the function for the table organization and its children tables: [location, region, province]
"""

from psycopg import Cursor
from uuid import UUID

from fertiscan.db.queries.errors import (
    LocationCreationError,
    LocationNotFoundError,
    LocationRetrievalError,
    OrganizationCreationError,
    OrganizationInformationCreationError,
    OrganizationInformationNotFoundError,
    OrganizationInformationRetrievalError,
    OrganizationInformationUpdateError,
    OrganizationNotFoundError,
    OrganizationRetrievalError,
    OrganizationUpdateError,
    ProvinceCreationError,
    ProvinceNotFoundError,
    ProvinceRetrievalError,
    RegionCreationError,
    RegionNotFoundError,
    RegionRetrievalError,
    handle_query_errors,
)


@handle_query_errors(OrganizationInformationCreationError)
def new_organization(cursor: Cursor, name, website, phone_number, address):
    """
    This function create a new organization in the database using a query.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the organization.
    - website (str): The website of the organization.
    - phone_number (str): The phone number of the organization.
    - address (str): The address of the organization.

    Returns:
    - str: The UUID of the organization
    """
    query = """
        INSERT INTO 
            organization (
                name,
                website,
                phone_number,
                address 
                )
        VALUES 
            (%s, %s, %s, %s)
        RETURNING 
            id
        """
    cursor.execute(query, (name, website, phone_number, address))
    if result := cursor.fetchone():
        return result[0]
    raise OrganizationCreationError("Failed to create Organization. No data returned.")


@handle_query_errors(OrganizationInformationCreationError)
def new_organization_information(
    cursor: Cursor,
    address: str,
    name: str,
    website: str,
    phone_number: str,
    label_id: UUID,
    edited: bool = False,
    is_main_contact: bool = False,
):
    """
    This function create a new organization information in the database using function.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the organization.
    - website (str): The website of the organization.
    - phone_number (str): The phone number of the organization.
    - label_id (str): The UUID of the label.
    - edited (bool): The edited status of the organization information.
    - is_main_contact (bool): The main contact status of the organization information.

    Returns:
    - str: The UUID of the organization information
    """
    if label_id is None:
        raise OrganizationInformationCreationError(
            "Label ID is required for organization information creation."
        )
    query = """
        SELECT new_organization_information(%s, %s, %s, %s, %s, %s, %s);
        """
    cursor.execute(
        query,
        (
            name,
            address,
            website,
            phone_number,
            edited,
            label_id,
            is_main_contact,
        ),
    )
    if result := cursor.fetchone():
        return result[0]
    raise OrganizationCreationError("Failed to create Organization. No data returned.")


@handle_query_errors(OrganizationInformationRetrievalError)
def get_organization_info(cursor: Cursor, information_id):
    """
    This function get a organization information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - information_id (str): The UUID of the organization information.

    Returns:
    - dict: The organization information
    """
    query = """
        SELECT 
            name, 
            website, 
            phone_number,
            address,
            label_id,
            edited,
            is_main_contact
        FROM 
            organization_information
        WHERE 
            id = %s
        """
    cursor.execute(query, (information_id,))
    if result := cursor.fetchone():
        return result
    raise OrganizationInformationNotFoundError(
        "Organization information not found with information_id: " + information_id
    )


def get_organizations_info_label(cursor: Cursor, label_id: UUID):
    """
    This function get a organization information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - information_id (str): The UUID of the organization information.

    Returns:
    - tuple: The organization informations
    """
    query = """
        SELECT 
            name, 
            website, 
            phone_number,
            address,
            edited,
            is_main_contact
        FROM 
            organization_information
        WHERE 
            label_id = %s
        """
    cursor.execute(query, (str(label_id),))
    if result := cursor.fetchall():
        return result
    raise OrganizationInformationNotFoundError(
        "Organization information not found with label_id: " + str(label_id)
    )


@handle_query_errors(OrganizationInformationRetrievalError)
def get_organizations_info_json(cursor: Cursor, label_id: UUID) -> dict:
    """
    This function get a organization information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - information_id (str): The UUID of the organization information.

    Returns:
    - dict: The organization information
    """
    query = """
        SELECT get_organizations_information_json(%s);
        """
    cursor.execute(query, (str(label_id),))

    if res := cursor.fetchone():
        return res[0]
    raise OrganizationInformationRetrievalError(
        "Failed to get Registration Numbers with the given label_id. No data returned."
    )


def get_organization_json(cursor: Cursor, fertilizer_id: UUID) -> dict:
    """
    This function get a organization information from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - fertilizer_id (str): The UUID of a Fertilizer owned by the orgganization.

    Returns:
    - dict: The organization information
    """
    query = """
        SELECT get_organization_json(%s);
        """
    cursor.execute(query, (str(fertilizer_id),))

    res = cursor.fetchone()
    if res is None or res[0] is None:
        # raise OrganizationNotFoundError
        # There might not be any organization information
        return {}
    if len(res[0]) == 2:
        return {**res[0][0], **res[0][1]}
    elif len(res[0]) == 1:
        return res[0][0]
    else:
        return {}


@handle_query_errors(OrganizationInformationUpdateError)
def update_organization_info(
    cursor: Cursor, information_id: UUID, name, website, phone_number
):
    """
    This function update a organization information in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - information_id (str): The UUID of the organization information.
    - name (str): The name of the organization.
    - website (str): The website of the organization.
    - phone_number (str): The phone number of the organization.

    Returns:
    - str: The UUID of the organization information
    """
    query = """
        UPDATE 
            organization_information
        SET 
            name = COALESCE(%s,name),
            website = COALESCE(%s,website),
            phone_number = COALESCE(%s,phone_number)
        WHERE 
            id = %s
        """
    cursor.execute(
        query,
        (
            name,
            website,
            phone_number,
            str(information_id),
        ),
    )
    return information_id


def upsert_organization_info(cursor: Cursor, organization_info, label_id: UUID):
    """
    This function upserts an organization information in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - organization_info (JSON: string): The organization information in a json.

    Returns:
    - json: The array of the organization information
    """
    query = """
        SELECT upsert_organization_info(%s, %s);
        """
    cursor.execute(
        query,
        (
            organization_info,
            str(label_id),
        ),
    )
    return cursor.fetchone()[0]


def upsert_organization(cursor: Cursor, organization_info_id: UUID):
    """
    This function upserts an organization information in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - organization_info (JSON: string): The organization information in a json.

    Returns:
    - str: The UUID of the organization information
    """
    query = """
        SELECT upsert_organization(%s);
        """
    cursor.execute(query, (str(organization_info_id),))
    if result := cursor.fetchone():
        return result[0]
    raise OrganizationUpdateError("Failed to update Organization. No data returned.")


@handle_query_errors(OrganizationRetrievalError)
def get_organization(cursor: Cursor, organization_id: UUID):
    """
    This function get a organization from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - organization_id (str): The UUID of the organization.

    Returns:
    - tuple: The organization
    """
    query = """
        SELECT 
            name,
            website,
            phone_number,
            address 
        FROM 
            organization
        WHERE 
            id = %s
        """
    cursor.execute(query, (str(organization_id),))
    if result := cursor.fetchone():
        return result
    raise OrganizationNotFoundError(
        "Organization not found with organization_id: " + organization_id
    )


@handle_query_errors(OrganizationRetrievalError)
def get_full_organization(cursor: Cursor, org_id):
    """
    This function get the full organization details from the database.
    This includes the location, region and province info of the organization.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - org_id (str): The UUID of the organization.

    Returns:
    - dict: The organization
    """
    query = """
        SELECT 
            organization.id, 
            organization.name, 
            organization.website, 
            organization.phone_number,
            organization.address,
            location.id, 
            location.name,
            location.address,
            location.address_number,
            location.city,
            location.postal_code,
            region.id,
            region.name,
            province.id,
            province.name
        FROM
            organization
        LEFT JOIN
            location
        ON
            organization.main_location_id = location.id
        LEFT JOIN
            region
        ON
            location.region_id = region.id
        LEFT JOIN
            province
        ON
            region.province_id = province.id
        WHERE 
            organization.id = %s
        """
    cursor.execute(query, (org_id,))
    return cursor.fetchone()


@handle_query_errors(LocationCreationError)
def new_location(cursor: Cursor, name, address, region_id, org_id=None):
    """
    This function create a new location in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - org_id (str): The UUID of the organization.
    - name (str): The name of the location.
    - address (str): The address of the location.
    - region_id (str): The UUID of the region.

    Returns:
    - str: The UUID of the location
    """
    query = """
        INSERT INTO 
            location (
                name, 
                address, 
                region_id,
                organization_id 
                )
        VALUES 
            (%s, %s, %s, %s)
        RETURNING 
            id
        """
    cursor.execute(
        query,
        (
            name,
            address,
            region_id,
            org_id,
        ),
    )
    if result := cursor.fetchone():
        return result[0]
    raise LocationCreationError("Failed to create Location. No data returned.")


@handle_query_errors(LocationRetrievalError)
def get_location(cursor: Cursor, location_id):
    """
    This function get a location from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - location_id (str): The UUID of the location.

    Returns:
    - dict: The location
    """
    query = """
        SELECT 
            name, 
            address, 
            region_id,
            organization_id 
        FROM 
            location
        WHERE 
            id = %s
        """
    cursor.execute(query, (location_id,))
    if result := cursor.fetchone():
        return result
    raise LocationNotFoundError("Location not found with location_id: " + location_id)


@handle_query_errors(LocationRetrievalError)
def get_full_location(cursor: Cursor, location_id):
    """
    This function get the full location details from the database.
    This includes the region and province info of the location.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - location_id (str): The UUID of the location.

    Returns:
    - dict: The location
    """
    query = """
        SELECT 
            location.id, 
            location.name,
            location.address,
            region.name,
            province.name
        FROM
            location
        LEFT JOIN
            region
        ON
            location.region_id = region.id
        LEFT JOIN
            province
        ON
            region.province_id = province.id
        WHERE 
            location.id = %s
        """
    cursor.execute(query, (location_id,))
    return cursor.fetchone()


@handle_query_errors(LocationRetrievalError)
def get_location_by_region(cursor: Cursor, region_id):
    """
    This function get a location from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - region_id (str): The UUID of the region.

    Returns:
    - dict: The location
    """
    query = """
        SELECT 
            id, 
            name, 
            address
        FROM 
            location
        WHERE 
            region_id = %s
        """
    cursor.execute(query, (region_id,))
    return cursor.fetchall()


@handle_query_errors(LocationRetrievalError)
def get_location_by_organization(cursor: Cursor, org_id):
    """
    This function get a location from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - org_id (str): The UUID of the organization.

    Returns:
    - dict: The location
    """
    query = """
        SELECT 
            id, 
            name, 
            address, 
            region_id 
        FROM 
            location
        WHERE 
            owner_id = %s
        """
    cursor.execute(query, (org_id,))
    return cursor.fetchall()


@handle_query_errors(RegionCreationError)
def new_region(cursor: Cursor, name, province_id):
    """
    This function create a new region in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - province_id (int): The id of the province.
    - name (str): The name of the region.

    Returns:
    - str: The UUID of the region
    """
    query = """
        INSERT INTO 
            region (
                province_id, 
                name 
                )
        VALUES 
            (%s, %s)
        RETURNING 
            id
        """
    cursor.execute(
        query,
        (
            province_id,
            name,
        ),
    )
    if result := cursor.fetchone():
        return result[0]
    raise RegionCreationError("Failed to create Region. No data returned.")


@handle_query_errors(RegionRetrievalError)
def get_region(cursor: Cursor, region_id):
    """
    This function get a region from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - region_id (int): The id of the region.

    Returns:
    - dict: The region
    """
    query = """
        SELECT 
            name,
            province_id
        FROM 
            region
        WHERE 
            id = %s
        """
    cursor.execute(query, (region_id,))
    if result := cursor.fetchone():
        return result
    raise RegionNotFoundError("region not found with region_id: " + str(region_id))


@handle_query_errors(RegionRetrievalError)
def get_full_region(cursor: Cursor, region_id):
    """
    This function get the full region details from the database.
    This includes the province info of the region.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - region_id (str): The UUID of the region.

    Returns:
    - dict: The region
    """
    query = """
        SELECT 
            region.id, 
            region.name,
            province.name
        FROM
            region
        LEFT JOIN
            province
        ON
            region.province_id = province.id
        WHERE 
            region.id = %s
        """
    cursor.execute(query, (region_id,))
    return cursor.fetchone()


@handle_query_errors(RegionRetrievalError)
def get_region_by_province(cursor: Cursor, province_id):
    """
    This function get a region from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - province_id (str): The UUID of the province.

    Returns:
    - dict: The region
    """
    query = """
        SELECT 
            id, 
            province_id, 
            name 
        FROM 
            region
        WHERE 
            province_id = %s
        """
    cursor.execute(query, (province_id,))
    return cursor.fetchall()


@handle_query_errors(ProvinceCreationError)
def new_province(cursor: Cursor, name):
    """
    This function create a new province in the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - name (str): The name of the province.

    Returns:
    - str: The UUID of the province
    """
    query = """
        INSERT INTO 
            province (
                name 
                )
        VALUES 
            (%s)
        RETURNING 
            id
        """
    cursor.execute(query, (name,))
    if result := cursor.fetchone():
        return result[0]
    raise ProvinceCreationError("Failed to create Province. No data returned.")


@handle_query_errors(ProvinceRetrievalError)
def get_province(cursor: Cursor, province_id):
    """
    This function get a province from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.
    - province_id (int): The UUID of the province.

    Returns:
    - dict: The province
    """
    query = """
        SELECT 
            name 
        FROM 
            province
        WHERE 
            id = %s
        """
    cursor.execute(query, (province_id,))
    if result := cursor.fetchone():
        return result
    raise ProvinceNotFoundError(
        "province not found with province_id: " + str(province_id)
    )


@handle_query_errors(ProvinceRetrievalError)
def get_all_province(cursor: Cursor):
    """
    This function get all province from the database.

    Parameters:
    - cursor (cursor): The cursor of the database.

    Returns:
    - dict: The province
    """
    query = """
        SELECT 
            id, 
            name 
        FROM 
            province
        """
    cursor.execute(query)
    return cursor.fetchall()
