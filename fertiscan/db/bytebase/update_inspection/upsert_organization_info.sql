-- Function to upsert organization information
DROP FUNCTION IF EXISTS "fertiscan_0.0.18".upsert_organization_info(jsonb, uuid);
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".upsert_organization_info(input_org_info jsonb, label_info_id uuid)
RETURNS jsonb AS $$
DECLARE
    record jsonb;
    address_str TEXT;
    location_id uuid;
    new_id uuid;
    index INT;
    result jsonb;
BEGIN
    index := 0;
    result := input_org_info;
    -- loop each orgs in the input_org_info
    for record in SELECT * FROM jsonb_array_elements(input_org_info)
    loop
        if record->>'id' IS NULL THEN
            new_id := new_organization_information(
                record->>'name',
                record->>'address',
                record->>'website',
                record->>'phone_number',
                TRUE,
                label_info_id,
                (record->>'is_main_contact')::boolean
            );
            -- add ids to the jsonb
            result := jsonb_set(result, array[index::text,'id'], to_jsonb(new_id));
        else
        -- UPDATE THE ORGANIZATION INFORMATION
            UPDATE organization_information SET
                "name" = record->>'name',
                "website" = record->>'website',
                "phone_number" = record->>'phone_number',
                "address" = address_str,
                "edited" = (record->>'edited')::boolean,
                "is_main_contact" = (record->>'is_main_contact')::boolean
            WHERE id = (record->>'id')::UUID;
        end if;
        index := index + 1;
    END LOOP;
RETURN result;
END;
$$ LANGUAGE plpgsql;
