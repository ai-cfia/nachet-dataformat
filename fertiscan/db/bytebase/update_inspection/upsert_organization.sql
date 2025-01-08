
DROP FUNCTION IF EXISTS "fertiscan_0.0.18".upsert_organization();
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".upsert_organization(org_info_id uuid)
RETURNS uuid 
LANGUAGE plpgsql
AS $function$
DECLARE
    record record;
    address_str TEXT;
    org_id uuid;
BEGIN
-- Select the row from the organization_information table
SELECT * INTO record FROM organization_information WHERE "id" = org_info_id;

-- Check if the organization exists
Select "id" INTO org_id FROM organization WHERE name ILIKE record.name;

-- UPSERT DATA INTO THE ORGANIZATION TABLE
IF org_id IS NULL THEN
    INSERT INTO organization ("name","website","phone_number","address","main_location_id")
    VALUES (
        record.name,
        record.website,
        record.phone_number,
        record.address,
        Null -- Not re-implemented yet
    )
    RETURNING "id" INTO org_id;
ELSE
    UPDATE organization SET
        "website" = record.website,
        "phone_number" = record.phone_number,
        "address" = record.address,
        "main_location_id" = Null -- Not re-implemented yet
    WHERE id = org_id;
END IF;
RETURN org_id;
END;
$function$;
