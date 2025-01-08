
drop FUNCTION IF EXISTS "fertiscan_0.0.18".update_registration_number;
-- Function to update guaranteed analysis: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".update_registration_number(
    p_label_id uuid,
    new_registration_numbers jsonb
)
RETURNS void AS $$
DECLARE
    reg_num_record jsonb;
BEGIN
    -- Delete existing guaranteed analysis for the given label_id
    DELETE FROM registration_number_information WHERE label_id = p_label_id;

		FOR reg_num_record IN SELECT * FROM jsonb_array_elements(new_registration_numbers)
        LOOP
            INSERT INTO registration_number_information (
                identifier,
                is_an_ingredient,
                label_id,
                edited
            )
            VALUES (
                reg_num_record->>'registration_number',
                (reg_num_record->>'is_an_ingredient')::boolean,
                p_label_id,
                (reg_num_record->>'edited')::boolean
            );
        END LOOP;
END;
$$ LANGUAGE plpgsql;
