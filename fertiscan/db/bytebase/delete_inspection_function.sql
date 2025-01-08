-- To avoid potential schema drift issues
SET search_path TO "fertiscan_0.0.18";

-- Trigger function to handle after organization_information delete for location deletion
DROP TRIGGER IF EXISTS after_organization_delete_main_location ON "fertiscan_0.0.18".organization;
drop FUNCTION IF EXISTS "fertiscan_0.0.18".after_org_delete_location_trig();
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".after_org_delete_location_trig()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.main_location_id IS NOT NULL THEN
        BEGIN
            DELETE FROM "fertiscan_0.0.18".location
            WHERE id = OLD.main_location_id;
        EXCEPTION WHEN foreign_key_violation THEN
            RAISE NOTICE 'Location % is still referenced by another record and cannot be deleted.', OLD.main_location_id;
        END;
    END IF;

    RETURN NULL;
END;
$$;

-- Trigger definition on organization_information table for location deletion
CREATE TRIGGER after_organization_delete_main_location
AFTER DELETE ON "fertiscan_0.0.18".organization
FOR EACH ROW
EXECUTE FUNCTION "fertiscan_0.0.18".after_org_delete_location_trig();

-- Function to delete an inspection and related data
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".delete_inspection(
    p_inspection_id uuid,
    p_inspector_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    inspection_record jsonb;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM "fertiscan_0.0.18".inspection 
        WHERE id = p_inspection_id 
        AND inspector_id = p_inspector_id
    ) THEN
        RAISE EXCEPTION 'Inspector % is not the creator of inspection %', p_inspector_id, p_inspection_id;
    END IF;

    -- Delete the inspection record and retrieve it
    WITH deleted_inspection AS (
        DELETE FROM "fertiscan_0.0.18".inspection
        WHERE id = p_inspection_id
        RETURNING *
    )
    SELECT row_to_json(deleted_inspection) 
    INTO inspection_record
    FROM deleted_inspection;

    -- Return the deleted inspection record
    RETURN inspection_record;
END;
$$;

-- Combined trigger function to handle after inspection delete for sample and label_information deletion
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".after_insp_delete_cleanup_trig()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    newest_inspection_id uuid;
BEGIN
    IF OLD.sample_id IS NOT NULL THEN
        DELETE FROM "fertiscan_0.0.18".sample
        WHERE id = OLD.sample_id;
    END IF;

    IF OLD.label_info_id IS NOT NULL THEN
        DELETE FROM "fertiscan_0.0.18".label_information
        WHERE id = OLD.label_info_id;
    END IF;

    IF OLD.fertilizer_id IS NOT NULL THEN
        -- Select the newest inspection for the fertilizer.latest_inspection_id
        SELECT id INTO newest_inspection_id 
        from "fertiscan_0.0.18".inspection
        WHERE fertilizer_id = OLD.fertilizer_id AND verified_date IS NOT NULL AND id != OLD.id
        ORDER BY verified_date DESC
        LIMIT 1;

        if newest_inspection_id IS NOT NULL THEN
            UPDATE "fertiscan_0.0.18".fertilizer
            SET latest_inspection_id = newest_inspection_id
            WHERE id = OLD.fertilizer_id;
        ELSE
        --This was the only inspection for the fertilizer so we delete it
            DELETE FROM "fertiscan_0.0.18".fertilizer
            WHERE id = OLD.fertilizer_id;
        end if;
    END IF;

    RETURN NULL;
END;
$$;

-- Trigger definition on inspection table for combined cleanup (sample and label_information deletion)
DROP TRIGGER IF EXISTS after_inspection_delete_cleanup ON "fertiscan_0.0.18".inspection;
CREATE TRIGGER after_inspection_delete_cleanup
AFTER DELETE ON "fertiscan_0.0.18".inspection
FOR EACH ROW
EXECUTE FUNCTION "fertiscan_0.0.18".after_insp_delete_cleanup_trig();
