
-- Function to update sub labels: delete old and insert new
Drop FUNCTION IF EXISTS "fertiscan_0.0.18".update_sub_labels(uuid, jsonb);
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".update_sub_labels(
    p_label_id uuid,
    new_sub_labels jsonb
)
RETURNS void AS $$
DECLARE
    sub_type_rec RECORD;
    fr_values jsonb;
    en_values jsonb;
    i int;
    max_length int;
    fr_value text;
    en_value text;
BEGIN
    -- Delete existing sub labels for the given label_id
    DELETE FROM sub_label WHERE label_id = p_label_id;

    -- Loop through each sub_type
    FOR sub_type_rec IN SELECT id, type_en FROM sub_type
    LOOP
        -- Extract the French and English arrays for the current sub_type
        fr_values := COALESCE(new_sub_labels->sub_type_rec.type_en->'fr', '[]'::jsonb);
        en_values := COALESCE(new_sub_labels->sub_type_rec.type_en->'en', '[]'::jsonb);

        -- Determine the maximum length of the arrays
        max_length := GREATEST(
            jsonb_array_length(fr_values),
            jsonb_array_length(en_values)
        );

        -- Check if lengths are not equal, and raise a notice
		IF jsonb_array_length(en_values) != jsonb_array_length(fr_values) THEN
			RAISE NOTICE 'Array length mismatch for sub_type: %, EN length: %, FR length: %', 
				sub_type_rec.type_en, jsonb_array_length(en_values), jsonb_array_length(fr_values);
		END IF;

        -- Loop through the indices up to the maximum length
        FOR i IN 0..(max_length - 1)
        LOOP
            -- Extract values or set to empty string if not present
            fr_value := fr_values->>i;
            en_value := en_values->>i;

            -- Insert sub label record
            INSERT INTO sub_label (
                text_content_fr, text_content_en, label_id, edited, sub_type_id
            )
            VALUES (
                fr_value,
                en_value,
                p_label_id,
                NULL,  -- not handled
                sub_type_rec.id
            );
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
