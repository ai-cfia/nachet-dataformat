SET search_path TO "fertiscan_0.0.17";

-- Function to upsert location information based on location_id and address
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".upsert_location(location_id uuid, address text)
RETURNS uuid AS $$
DECLARE
    new_location_id uuid;
BEGIN
    IF address IS NULL THEN
        RAISE EXCEPTION 'Address cannot be null';
        RETURN NULL;
    END IF;
    -- Upsert the location
    INSERT INTO location (id, address)
    VALUES (COALESCE(location_id, public.uuid_generate_v4()), address)
    ON CONFLICT (id) -- Specify the unique constraint column for conflict handling
    DO UPDATE SET address = EXCLUDED.address
    RETURNING id INTO new_location_id;

    RETURN new_location_id;
END;
$$ LANGUAGE plpgsql;


-- Function to upsert organization information
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".upsert_organization_info(input_org_info jsonb)
RETURNS uuid AS $$
DECLARE
    organization_info_id uuid;
    location_id uuid;
    address_str text;
BEGIN
    -- Skip processing if the input JSON object is empty or null
    IF jsonb_typeof(input_org_info) = 'null' OR NOT EXISTS (SELECT 1 FROM jsonb_object_keys(input_org_info)) or
    COALESCE(input_org_info->>'name', 
		input_org_info->>'website', 
		input_org_info->>'phone_number', 
		input_org_info->>'address',
		 '') = ''  THEN
         RAISE WARNING 'Organization information is empty or null';
        RETURN NULL;
    ELSE
        
        address_str := input_org_info->>'address';

        -- CHECK IF ADRESS IS NULL
        IF address_str IS NULL THEN
            RAISE WARNING 'Address cannot be null';
        ELSE 
            -- Check if organization location exists by address
            SELECT id INTO location_id
            FROM location
            WHERE location.address ILIKE address_str
            LIMIT 1;
                -- Use upsert_location to insert or update the location
            location_id := upsert_location(location_id, address_str);
        END IF;

        -- Extract the organization info ID from the input JSON or generate a new UUID if not provided
        organization_info_id := COALESCE(NULLIF(input_org_info->>'id', '')::uuid, public.uuid_generate_v4());

        -- Upsert organization information
        INSERT INTO organization_information (id, name, website, phone_number, location_id)
        VALUES (
            organization_info_id,
            input_org_info->>'name',
            input_org_info->>'website',
            input_org_info->>'phone_number',
            location_id
        )
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            website = EXCLUDED.website,
            phone_number = EXCLUDED.phone_number,
            location_id = EXCLUDED.location_id
        RETURNING id INTO organization_info_id;

        RETURN organization_info_id;
    end if;
END;
$$ LANGUAGE plpgsql;


-- Function to update metrics: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_metrics(
    p_label_id uuid,
    metrics jsonb
)
RETURNS void AS $$
DECLARE
    metric_record jsonb;
    metric_type text;
    metric_value float;
    metric_unit text;
    unit_id uuid;
    edited_value boolean;
BEGIN
    -- Delete existing metrics for the given label_id
    DELETE FROM metric WHERE label_id = p_label_id;

    -- Handle weight metrics separately
    IF metrics ? 'weight' THEN
        FOR metric_record IN SELECT * FROM jsonb_array_elements(metrics->'weight')
        LOOP
            metric_value := NULLIF(metric_record->>'value', '')::float;
            metric_unit := metric_record->>'unit';
            edited_value := COALESCE((metric_record->>'edited')::boolean, FALSE);
            
            -- Proceed only if the value is not NULL
            IF (metric_value IS NOT NULL) AND (metric_unit IS NOT NULL) THEN
                -- Check if the metric unit is null
                IF metric_unit IS NULL THEN
                    RAISE WARNING 'Metric unit is null';
                ELSE
                    -- Fetch or insert the unit ID
                    SELECT id INTO unit_id FROM unit WHERE unit = metric_unit LIMIT 1;
                    IF unit_id IS NULL THEN
                        INSERT INTO unit (unit) VALUES (metric_unit) RETURNING id INTO unit_id;
                    END IF;
                END IF;
                -- Insert metric record for weight
                INSERT INTO metric (id, value, unit_id, metric_type, label_id,edited)
                VALUES (public.uuid_generate_v4(), metric_value, unit_id, 'weight'::metric_type, p_label_id,edited_value);
            END IF;
        END LOOP;
    END IF;

    -- Handle density and volume metrics
    FOREACH metric_type IN ARRAY ARRAY['density', 'volume']
    LOOP
        IF metrics ? metric_type THEN
            metric_record := metrics->metric_type;
            metric_value := NULLIF(metric_record->>'value', '')::float;
            metric_unit := metric_record->>'unit';
            edited_value := COALESCE((metric_record->>'edited')::boolean, FALSE);
                        -- Proceed only if the value is not NULL
            IF (metric_value IS NOT NULL) AND (metric_unit IS NOT NULL) THEN
                -- Check if the metric unit is null
                IF metric_unit IS NULL THEN
                    RAISE WARNING 'Metric unit is null';
                ELSE
                    -- Fetch or insert the unit ID
                    SELECT id INTO unit_id FROM unit WHERE unit = metric_unit LIMIT 1;
                    IF unit_id IS NULL THEN
                        INSERT INTO unit (unit) VALUES (metric_unit) RETURNING id INTO unit_id;
                    END IF;
                END IF;
                -- Insert metric record for weight
                INSERT INTO metric (id, value, unit_id, metric_type, label_id,edited)
                VALUES (public.uuid_generate_v4(), metric_value, unit_id, metric_type::metric_type, p_label_id,edited_value);
            END IF;
        END IF;
    END LOOP;

END;
$$ LANGUAGE plpgsql;


-- Function to update specifications: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_specifications(
    p_label_id uuid,
    new_specifications jsonb
)
RETURNS void AS $$
DECLARE
    spec_language text;
    spec_record jsonb;
BEGIN
    -- Delete existing specifications for the given label_id
    DELETE FROM specification WHERE label_id = p_label_id;

    -- Insert new specifications
    FOR spec_language IN SELECT * FROM jsonb_object_keys(new_specifications)
    LOOP
        FOR spec_record IN SELECT * FROM jsonb_array_elements(new_specifications -> spec_language)
        LOOP
            -- CHECK IF ANY OF THE VALUES ARE NOT NULL
            IF COALESCE(
                spec_record->>'humidity', 
                spec_record->>'ph', 
                spec_record->>'solubility',
                '') <> ''
            THEN
                -- Insert each specification record
                INSERT INTO specification (
                    humidity, ph, solubility, edited, label_id, language
                )
                VALUES (
                    (spec_record->>'humidity')::float,
                    (spec_record->>'ph')::float,
                    (spec_record->>'solubility')::float,
                    COALESCE(spec_record->>'edited','False')::boolean,
                    p_label_id,
                    spec_language::language
                );
            ELSE
                RAISE WARNING 'ALL SPECIFICATION VALUES WERE NULL';
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- Function to update ingredients: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_ingredients(
    p_label_id uuid,
    new_ingredients jsonb
)
RETURNS void AS $$
DECLARE
    ingredient_language text;
    ingredient_record jsonb;
BEGIN
    -- Delete existing ingredients for the given label_id
    DELETE FROM ingredient WHERE label_id = p_label_id;

    -- Insert new ingredients
    FOR ingredient_language IN SELECT * FROM jsonb_object_keys(new_ingredients)
    LOOP
        FOR ingredient_record IN SELECT * FROM jsonb_array_elements(new_ingredients -> ingredient_language)
        LOOP
            -- CHECK IF ANY OF THE VALUES ARE NOT NULL
            IF COALESCE(
                ingredient_record->>'name', 
                ingredient_record->>'value', 
                ingredient_record->>'unit',
                '') <> ''
            THEN
                -- Insert each ingredient record
                INSERT INTO ingredient (
                    organic, active, name, value, unit, edited, label_id, language
                )
                VALUES (
                    NULL, -- not yet handled
                    NULL, -- not yet handled
                    ingredient_record->>'name',
                    NULLIF(ingredient_record->>'value', '')::float,
                    ingredient_record->>'unit',
                    FALSE, -- not yet handled
                    p_label_id,
                    ingredient_language::language
                );
            ELSE
                RAISE WARNING 'ALL INGREDIENT VALUES WERE NULL';
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- Function to update micronutrients: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_micronutrients(
    p_label_id uuid,
    new_micronutrients jsonb
)
RETURNS void AS $$
DECLARE
    nutrient_language text;
    nutrient_record jsonb;
BEGIN
    -- Delete existing micronutrients for the given label_id
    DELETE FROM micronutrient WHERE label_id = p_label_id;

    -- Insert new micronutrients
    FOR nutrient_language IN SELECT * FROM jsonb_object_keys(new_micronutrients)
    LOOP
        FOR nutrient_record IN SELECT * FROM jsonb_array_elements(new_micronutrients -> nutrient_language)
        LOOP
            -- CHECK IF ANY OF THE VALUES ARE NOT NULL
            IF COALESCE(
                nutrient_record->>'name', 
                nutrient_record->>'value', 
                nutrient_record->>'unit',
                '') <> ''
            THEN
                -- Insert each micronutrient record
                INSERT INTO micronutrient (
                    read_name, value, unit, edited, label_id, language
                )
                VALUES (
                    nutrient_record->>'name',
                    NULLIF(nutrient_record->>'value', '')::float,
                    nutrient_record->>'unit',
                    FALSE,  -- not handled
                    p_label_id,
                    nutrient_language::language
                );
            ELSE
                RAISE WARNING 'ALL MICRONUTRIENT VALUES WERE NULL';
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

drop FUNCTION IF EXISTS "fertiscan_0.0.17".update_guaranteed;
-- Function to update guaranteed analysis: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_guaranteed(
    p_label_id uuid,
    new_guaranteed jsonb
)
RETURNS void AS $$
DECLARE
    guaranteed_record jsonb;
    language_record record;
    guaranteed_analysis_language text;
BEGIN
    -- Delete existing guaranteed analysis for the given label_id
    DELETE FROM guaranteed WHERE label_id = p_label_id;

	-- Loop through each language ('en' and 'fr')
    FOR guaranteed_analysis_language  IN SELECT unnest(enum_range(NULL::"fertiscan_0.0.17".LANGUAGE))
	LOOP
		FOR guaranteed_record IN SELECT * FROM jsonb_array_elements(new_guaranteed->guaranteed_analysis_language)
		LOOP
            --CHECK IF ANY OF THE VALUES ARE NOT NULL
            IF COALESCE(
                guaranteed_record->>'name', 
                guaranteed_record->>'value', 
                guaranteed_record->>'unit',
                '') <> ''
            THEN
                -- Insert each guaranteed analysis record
                INSERT INTO guaranteed (
                    read_name, value, unit, edited, label_id, language
                )
                VALUES (
                    guaranteed_record->>'name',
                    NULLIF(guaranteed_record->>'value', '')::float,
                    guaranteed_record->>'unit',
                    FALSE,  -- not handled
                    p_label_id,
                    guaranteed_analysis_language::language
                );
            ELSE
                RAISE EXCEPTION 'ALL GUARANTEED ANALYSIS VALUES WERE NULL';
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- Function to check if both text_content_fr and text_content_en are NULL or empty, and skip insertion if true
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".check_null_or_empty_sub_label()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if both text_content_fr and text_content_en are NULL or empty
    IF (NEW.text_content_fr IS NULL OR NEW.text_content_fr = '') AND 
       (NEW.text_content_en IS NULL OR NEW.text_content_en = '') THEN
        -- Raise an exception and skip the insertion
        RAISE EXCEPTION 'Skipping insertion because both text_content_fr and text_content_en are NULL or empty';
        RETURN NULL;
    END IF;

    -- Replace NULL with empty strings
    IF NEW.text_content_fr IS NULL THEN
        NEW.text_content_fr := '';
    END IF;

    IF NEW.text_content_en IS NULL THEN
        NEW.text_content_en := '';
    END IF;

    -- Allow the insert if at least one is not NULL or empty
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Trigger to call check_null_or_empty_sub_label() before inserting into sub_label
DROP TRIGGER IF EXISTS before_insert_sub_label ON "fertiscan_0.0.17".sub_label;
CREATE TRIGGER before_insert_sub_label
BEFORE INSERT ON "fertiscan_0.0.17".sub_label
FOR EACH ROW
EXECUTE FUNCTION "fertiscan_0.0.17".check_null_or_empty_sub_label();


-- Function to update sub labels: delete old and insert new
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_sub_labels(
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

Drop FUNCTION IF EXISTS "fertiscan_0.0.17".upsert_inspection;
-- Function to upsert inspection information
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".upsert_inspection(
    p_inspection_id uuid,
    p_label_info_id uuid,
    p_inspector_id uuid,
    p_sample_id uuid,
    p_picture_set_id uuid,
    p_verified boolean
)
RETURNS uuid AS $$
DECLARE
    inspection_id uuid;
BEGIN

    IF p_inspection_id IS NULL THEN 
        RAISE EXCEPTION 'Inspection ID is required';
    END IF;
    -- Use provided inspection_id or generate a new one if not provided
    inspection_id := p_inspection_id;

    -- Upsert inspection information
    INSERT INTO inspection (
        id, label_info_id, inspector_id, sample_id, picture_set_id, verified, upload_date, updated_at, original_dataset
    )
    VALUES (
        inspection_id,
        p_label_info_id,
        p_inspector_id,
        NULL,  -- not handled yet
        p_picture_set_id,
        p_verified,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP,
        p_original_dataset
    )
    ON CONFLICT (id) DO UPDATE
    SET 
        label_info_id = EXCLUDED.label_info_id,
        inspector_id = EXCLUDED.inspector_id,
        sample_id = NULL,  -- not handled yet
        picture_set_id = EXCLUDED.picture_set_id,
        verified = EXCLUDED.verified,
        updated_at = CURRENT_TIMESTAMP  -- Update timestamp on conflict
    RETURNING id INTO inspection_id;

    RETURN inspection_id;
END;
$$ LANGUAGE plpgsql;


-- Function to upsert fertilizer information based on unique fertilizer name
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".upsert_fertilizer(
    p_name text,
    p_registration_number text,
    p_owner_id uuid,
    p_latest_inspection_id uuid
)
RETURNS uuid AS $$
DECLARE
    fertilizer_id uuid;
BEGIN
    -- Upsert fertilizer information
    INSERT INTO fertilizer (
        name, registration_number, upload_date, update_at, owner_id, latest_inspection_id
    )
    VALUES (
        p_name,
        p_registration_number,
        CURRENT_TIMESTAMP,  -- Set upload date to current timestamp
        CURRENT_TIMESTAMP,  -- Set update date to current timestamp
        p_owner_id,
        p_latest_inspection_id
    )
    ON CONFLICT (name) DO UPDATE
    SET
        registration_number = EXCLUDED.registration_number,
        update_at = CURRENT_TIMESTAMP,  -- Update the update_at timestamp
        owner_id = EXCLUDED.owner_id,
        latest_inspection_id = EXCLUDED.latest_inspection_id
    RETURNING id INTO fertilizer_id;

    RETURN fertilizer_id;
END;
$$ LANGUAGE plpgsql;


-- Function to update inspection data and related entities, returning an updated JSON
CREATE OR REPLACE FUNCTION "fertiscan_0.0.17".update_inspection(
    p_inspection_id uuid,
    p_inspector_id uuid,
    p_input_json jsonb
)
RETURNS jsonb AS $$
#variable_conflict use_variable
DECLARE
    inspection_id uuid := p_inspection_id;
    json_inspection_id uuid;
    company_info_id uuid;
    manufacturer_info_id uuid;
    label_info_id_value uuid;
    organization_id uuid;
    updated_json jsonb := p_input_json;
    fertilizer_name text;
    registration_number text;
    verified_bool boolean;
    existing_inspector_id uuid;
    registration_number_json jsonb;
BEGIN
    -- Check if the provided inspection_id matches the one in the input JSON
    json_inspection_id := (p_input_json->>'inspection_id')::uuid;
    IF json_inspection_id IS NOT NULL AND json_inspection_id != inspection_id THEN
        RAISE EXCEPTION 'Inspection ID mismatch: % vs %', inspection_id, json_inspection_id;
    END IF;

    -- Check if the provided inspector_id matches the existing one
    SELECT inspector_id INTO existing_inspector_id
    FROM inspection
    WHERE id = p_inspection_id;
    IF existing_inspector_id IS NULL OR existing_inspector_id != p_inspector_id THEN
        RAISE EXCEPTION 'Unauthorized: Inspector ID mismatch or inspection not found';
    END IF;

    -- Check if the provided label_id matches the existing one
    SELECT label_info_id INTO label_info_id_value
    FROM inspection
    WHERE id = p_inspection_id;
    IF label_info_id_value IS NULL OR label_info_id_value != (p_input_json->'product'->>'label_id')::uuid THEN
        RAISE EXCEPTION 'Label ID mismatch or inspection not found';
    END IF;

    -- Upsert company information and get the ID
    company_info_id := upsert_organization_info(p_input_json->'company');
    IF company_info_id IS NOT NULL THEN
        updated_json := jsonb_set(updated_json, '{company,id}', to_jsonb(company_info_id));
    END IF;

    -- Upsert manufacturer information and get the ID
    manufacturer_info_id := upsert_organization_info(p_input_json->'manufacturer');
    IF manufacturer_info_id IS NOT NULL THEN
        updated_json := jsonb_set(updated_json, '{manufacturer,id}', to_jsonb(manufacturer_info_id));
    END IF;

    -- update Label information
    UPDATE label_information
    SET
    id = label_info_id_value,
    product_name = p_input_json->'product'->>'name', 
    lot_number = p_input_json->'product'->>'lot_number',
    npk = p_input_json->'product'->>'npk',
    n = (NULLIF(p_input_json->'product'->>'n', '')::float),
    p = (NULLIF(p_input_json->'product'->>'p', '')::float),
    k = (NULLIF(p_input_json->'product'->>'k', '')::float),
    guaranteed_title_en = p_input_json->'guaranteed_analysis'->'title'->>'en',
    guaranteed_title_fr = p_input_json->'guaranteed_analysis'->'title'->>'fr',
    title_is_minimal = (p_input_json->'guaranteed_analysis'->>'is_minimal')::boolean,
    "company_info_id" = company_info_id, 
    "manufacturer_info_id" = manufacturer_info_id,
    record_keeping = (p_input_json->'product'->>'record_keeping')::boolean
    WHERE id = label_info_id_value;

    updated_json := jsonb_set(updated_json, '{product,label_id}', to_jsonb(label_info_id_value));

    -- Update metrics related to the label
    PERFORM update_metrics(label_info_id_value, p_input_json->'product'->'metrics');

    -- Update specifications related to the label
    -- PERFORM update_specifications(label_info_id_value, p_input_json->'specifications');

    -- Update ingredients related to the label
     PERFORM update_ingredients(label_info_id_value, p_input_json->'ingredients');

    -- Update micronutrients related to the label
    -- PERFORM update_micronutrients(label_info_id_value, p_input_json->'micronutrients');

    -- Update guaranteed analysis related to the label
    PERFORM update_guaranteed(label_info_id_value, p_input_json->'guaranteed_analysis');

    -- Update sub labels related to the label
    PERFORM update_sub_labels(label_info_id_value, p_input_json);

    -- Update the registration number information related to the label
    PERFORM update_registration_number(label_info_id_value, p_input_json->'product'->'registration_numbers');

    -- Update the inspection record
    verified_bool := (p_input_json->>'verified')::boolean;

    UPDATE 
        inspection
    SET 
        id = inspection_id,
        label_info_id = label_info_id_value,
        inspector_id = p_inspector_id,
        sample_id = COALESCE(p_input_json->>'sample_id', NULL)::uuid,
        picture_set_id = COALESCE(p_input_json->>'picture_set_id', NULL)::uuid,
        verified = verified_bool,
        updated_at = CURRENT_TIMESTAMP,  -- Update timestamp on conflict
        inspection_comment = p_input_json->>'inspection_comment'
    WHERE 
        id = p_inspection_id;

    -- Update the inspection ID in the output JSON
    updated_json := jsonb_set(updated_json, '{inspection_id}', to_jsonb(inspection_id));

    -- Check if the verified field is true, and upsert fertilizer if so
    IF verified_bool THEN
        fertilizer_name := p_input_json->'product'->>'name';
        registration_number := NULL;
        -- loop through registration numbers to find the one to use
        for registration_number_json in SELECT jsonb_array_elements_text(p_input_json->'product'->'registration_numbers')
        LOOP
            if (registration_number_json->>'is_an_ingredient')::boolean THEN
                registration_number := registration_number_json->>'registration_number';
            END IF;
        END LOOP;

        -- Insert organization and get the organization_id
        IF manufacturer_info_id IS NOT NULL THEN
            INSERT INTO organization (information_id, main_location_id)
            VALUES (manufacturer_info_id, NULL) -- TODO: main_location_id not yet handled
            RETURNING id INTO organization_id;
        ELSE
            organization_id := NULL;
        END IF;

        -- Upsert the fertilizer record
        PERFORM upsert_fertilizer(
            fertilizer_name,
            registration_number,
            organization_id,
            inspection_id
        );
    END IF;

    -- Return the updated JSON without fertilizer_id
    RETURN updated_json;

END;
$$ LANGUAGE plpgsql;
