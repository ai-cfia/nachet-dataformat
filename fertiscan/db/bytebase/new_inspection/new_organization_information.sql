
DROP FUNCTION IF EXISTS "fertiscan_0.0.18".new_organization_located(TEXT, TEXT, TEXT, TEXT, BOOLEAN, UUID, BOOLEAN);
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_organization_information(
    name TEXT,
    address_str TEXT,
    website TEXT,
    phone_number TEXT,
    edited BOOLEAN = FALSE,
    label_id UUID = NULL,
    is_main_contact_val BOOLEAN = FALSE
    )
RETURNS uuid 
LANGUAGE plpgsql
AS $function$
DECLARE
    record RECORD;
    organization_id uuid;
BEGIN
-- CHECK IF ANY OF THE INPUTS ARE NOT NULL
IF COALESCE(name, address_str, website, phone_number,'') = '' THEN
    RAISE EXCEPTION 'ALL of the input parameters are null';
END IF;
IF label_id IS NULL THEN
    RAISE EXCEPTION 'Label_id cannot be null when creating an organization_information';
END IF;
	INSERT INTO organization_information ("name","website","phone_number","address","edited","label_id","is_main_contact")
	VALUES (
	        name,
            website,
            phone_number,
            address_str,
            edited,
            label_id,
            is_main_contact_val
	)
	RETURNING id INTO organization_id;

    RETURN organization_id;
END;
$function$;
