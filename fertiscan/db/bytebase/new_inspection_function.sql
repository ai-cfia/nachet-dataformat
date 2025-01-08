
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_inspection(user_id uuid, picture_set_id uuid, input_json jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    label_info_id uuid;
    sub_type_rec RECORD;
    fr_values jsonb;
    en_values jsonb;
    record jsonb;
    inspection_id_value uuid;
    organization_id uuid;
    location_id uuid;
	weight_id uuid;
	density_id uuid;
	volume_id uuid;
	micronutrient_id uuid;
	ingredient_id uuid;
	guaranteed_analysis_id uuid;
	registration_number_id uuid;
	time_id uuid;
    unit_id uuid;
    specification_id uuid;
    sub_label_id uuid;
    metric_type_id uuid;
	key_string text;
    read_value text;
    read_unit text;
    read_language text;
    value_float float;
    ingredient_language text;
	micronutrient_language text;
	name_string text;
	address_string text;
	website_string text;
	phone_number_string text;
    result_json jsonb := '{}';
	guaranteed_analysis_language text;
	max_length int;
    fr_value text;
    en_value text;
	flag boolean;
	counter int;
	orgs_ids uuid[];
BEGIN
	
-- COMPANY
--	name_string := input_json->'company'->>'name';
--	address_string := input_json->'company'->>'address';
--	website_string := input_json->'company'->>'website';
--	phone_number_string := input_json->'company'->>'phone_number';
--	IF COALESCE(name_string, 
--		address_string, 
--		website_string, 
--		phone_number_string,
--		 '') <> ''
--	THEN
--		company_id := "fertiscan_0.0.18".new_organization_info_located(
--			input_json->'company'->>'name',
--			input_json->'company'->>'address',
--			input_json->'company'->>'website',
--			input_json->'company'->>'phone_number',
--			FALSE
--		);
--	
--		-- Update input_json with company_id
--		input_json := jsonb_set(input_json, '{company,id}', to_jsonb(company_id));
--	END IF;
-- COMPANY END

-- MANUFACTURER
--	name_string := input_json->'manufacturer'->>'name';
--	address_string := input_json->'manufacturer'->>'address';
--	website_string := input_json->'manufacturer'->>'website';
--	phone_number_string := input_json->'manufacturer'->>'phone_number';
--	-- Check if any of the manufacturer fields are not null
--	IF COALESCE(name_string, 
--		address_string, 
--		website_string, 
--		phone_number_string,
--		 '') <> '' 
--	THEN
--		manufacturer_id := "fertiscan_0.0.18".new_organization_info_located(
--			input_json->'manufacturer'->>'name',
--			input_json->'manufacturer'->>'address',
--			input_json->'manufacturer'->>'website',
--			input_json->'manufacturer'->>'phone_number',
--			FALSE
--		);
--		-- Update input_json with company_id
--		input_json := jsonb_set(input_json, '{manufacturer,id}', to_jsonb(manufacturer_id));
--	end if;
	-- Manufacturer end

-- LABEL INFORMATION
	label_info_id := "fertiscan_0.0.18".new_label_information(
		input_json->'product'->>'name',
		input_json->'product'->>'lot_number',
		input_json->'product'->>'npk',
		(input_json->'product'->>'n')::float,
		(input_json->'product'->>'p')::float,
		(input_json->'product'->>'k')::float,
		input_json->'guaranteed_analysis'->'title'->>'en',
		input_json->'guaranteed_analysis'->'title'->>'fr',
		(input_json->'guaranteed_analysis'->>'is_minimal')::boolean,
		Null -- record_keeping not handled yet
	);
		
	-- Update input_json with label_id
	input_json := jsonb_set(input_json, '{product,label_id}', to_jsonb(label_info_id));

--LABEL END

--WEIGHT
	-- Loop through each element in the 'weight' array
    FOR record IN SELECT * FROM jsonb_array_elements(input_json-> 'product' -> 'metrics' -> 'weight')
    LOOP
        -- Extract the value and unit from the current weight record
        read_value := record->>'value';
       -- CHECK IF ANY FIELD IS NOT NULL
		IF COALESCE(read_value,
			record->>'unit',
			'') <> '' 
		THEN
			-- Insert the new weight
			weight_id = "fertiscan_0.0.18".new_metric_unit(
				read_value::float,
				record->>'unit',
				label_info_id,
				'weight'::"fertiscan_0.0.18".metric_type,
				FALSE
			);
		END IF;
	 END LOOP;
-- Weight end
	
--DENSITY
 	read_value := input_json -> 'product' -> 'metrics' ->'density'->> 'value';
 	read_unit := input_json -> 'product' -> 'metrics' -> 'density'->> 'unit';
	-- Check if density_value is not null and handle density_unit
	IF read_value IS NOT NULL THEN
	    --CHECK IS ANY FIELD IS NOT NULL
		IF COALESCE(read_value,
			read_unit,
			'') <> ''
		THEN
			density_id := "fertiscan_0.0.18".new_metric_unit(
				read_value::float,
				read_unit,
				label_info_id,
				'density'::"fertiscan_0.0.18".metric_type,
				FALSE
			);
		END IF;
	END IF;
-- DENSITY END

--VOLUME
 	read_value := input_json -> 'product' -> 'metrics' -> 'volume'->> 'value';
 	read_unit := input_json -> 'product' -> 'metrics' -> 'volume'->> 'unit';
	-- Check if density_value is not null and handle density_unit
	IF read_value IS NOT NULL THEN
		value_float = read_value::float;
	  	-- CHECK IF ANY FIELD IS NOT NULL
		IF COALESCE(read_value,
			read_unit,
			'') <> '' 
		THEN
			-- Insert the new volume
			volume_id := "fertiscan_0.0.18".new_metric_unit(
				value_float,
				read_unit,
				label_info_id,
				'volume'::"fertiscan_0.0.18".metric_type,
				FALSE
			);
		END IF;
	END IF;
-- Volume end
   
-- SPECIFICATION
--	FOR ingredient_language IN SELECT * FROM jsonb_object_keys(input_json->'specifications')
--	LOOP
--		FOR record IN SELECT * FROM jsonb_array_elements(input_json->'specifications'->ingredient_language)
--		LOOP
--			-- Check if any of the fields are not null
--			IF COALESCE(record->>'humidity', 
--				record->>'ph', 
--				record->>'solubility',
--				'') <> '' 
--			THEN
--				-- Insert the new specification
--				specification_id := "fertiscan_0.0.18".new_specification(
--					(record->>'humidity')::float,
--					(record->>'ph')::float,
--					(record->>'solubility')::float,
--					ingredient_language::"fertiscan_0.0.18".language,
--					label_info_id,
--					FALSE
--				);	
--			END IF;
--		END LOOP;
--	END LOOP;
-- SPECIFICATION END

-- --INGREDIENTS
 	-- Loop through each language ('en' and 'fr')
 	FOR ingredient_language  IN SELECT * FROM jsonb_object_keys(input_json->'ingredients')
 	LOOP
        -- Loop through each ingredient in the current language
        FOR record IN SELECT * FROM jsonb_array_elements(input_json->'ingredients'->ingredient_language )
        LOOP
			-- Extract values from the current ingredient record
			read_value := record->> 'value';
				read_unit := record ->> 'unit';
			-- Check if ANY field is not null
			IF COALESCE(record->>'name', 
				read_value, 
				read_unit,
				'') <> '' 
			THEN
				-- Insert the new ingredient
				ingredient_id := "fertiscan_0.0.18".new_ingredient(
					record->>'name',
					read_value::float,
					read_unit,
					label_info_id,
					ingredient_language::"fertiscan_0.0.18".language,
					NULL, --We cant tell atm
					NULL,  --We cant tell atm
					FALSE  --preset
				);
			END IF;
    	END LOOP;
 	END LOOP;
-- INGREDIENTS ENDS

-- SUB LABELS
	-- Loop through each sub_type
   FOR sub_type_rec IN SELECT id, type_en FROM sub_type
	LOOP
		-- Extract the French and English arrays for the current sub_type
		key_string := sub_type_rec.type_en;
		en_values := COALESCE(input_json -> key_string -> 'en', '[]'::jsonb);
		fr_values := COALESCE(input_json -> key_string -> 'fr', '[]'::jsonb);

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

			-- Insert sub-label without deleting existing data
			sub_label_id := "fertiscan_0.0.18".new_sub_label(
				fr_value,
				en_value,
				label_info_id,
				sub_type_rec.id,
				FALSE
			);
		END LOOP;
	END LOOP;
-- SUB_LABEL END
  
  -- MICRO NUTRIENTS
--		-- Loop through each language ('en' and 'fr')
--    FOR micronutrient_language  IN SELECT * FROM jsonb_object_keys(input_json->'micronutrients')
--	LOOP
--		FOR record IN SELECT * FROM jsonb_array_elements(input_json->'micronutrients'->micronutrient_language)
--		LOOP
--			-- Check if any of the fields are not null
--			IF COALESCE(record->>'name', 
--				record->>'value', 
--				record->>'unit',
--				'') <> '' 
--			THEN
--				-- Insert the new Micronutrient
--				micronutrient_id := "fertiscan_0.0.18".new_micronutrient(
--					record->> 'name',
--					(record->> 'value')::float,
--					record->> 'unit',
--					label_info_id,
--					micronutrient_language::"fertiscan_0.0.18".language
--				);
--			END IF;
--		END LOOP;
--	END LOOP;
--MICRONUTRIENTS ENDS

-- GUARANTEED

		-- Loop through each language ('en' and 'fr')
    FOR guaranteed_analysis_language  IN SELECT unnest(enum_range(NULL::"fertiscan_0.0.18".LANGUAGE))
	LOOP
		FOR record IN SELECT * FROM jsonb_array_elements(input_json->'guaranteed_analysis'->guaranteed_analysis_language)
		LOOP
			-- Check if any of the fields are not null
			IF COALESCE(record->>'name', 
				record->>'value', 
				record->>'unit',
				'') <> '' 
			THEN
				-- Insert the new guaranteed_analysis
				guaranteed_analysis_id := "fertiscan_0.0.18".new_guaranteed_analysis(
					record->>'name',
					(record->>'value')::float,
					record->>'unit',
					label_info_id,
					guaranteed_analysis_language::"fertiscan_0.0.18".language,
					FALSE,
					NULL -- We arent handeling element_id yet
				);
			END IF;
		END LOOP;
	END LOOP;
-- GUARANTEED END	

-- REGISTRATION NUMBER

	-- Loop through each registration number in the JSON array
	FOR record IN SELECT * FROM jsonb_array_elements(input_json-> 'product'-> 'registration_numbers')
	LOOP
		-- Check make sure we dont create an empty registration number
		IF COALESCE(record->>'registration_number', 
					'') <> '' 
		THEN
			-- Insert the new registration number
			registration_number_id := "fertiscan_0.0.18".new_registration_number(
				record->>'registration_number',
				label_info_id,
				(record->>'is_an_ingredient')::BOOLEAN,
				null,
				FALSE
			);
		END IF;
	END LOOP;

-- REGISTRATION NUMBER END

-- ORGANIZATIONS INFO
	flag := TRUE;
	counter := 0;
	FOR record in SELECT * FROM jsonb_array_elements(input_json->'organizations')
	LOOP
		-- Check if any of the fields are not null
		IF COALESCE(record->>'name', 
			record->>'address', 
			record->>'website',
			record->>'phone_number',
			'') <> '' 
		THEN
			-- Insert the new organization info
			organization_id := "fertiscan_0.0.18".new_organization_information(
				record->>'name',
				record->>'address',
				record->>'website',
				record->>'phone_number',
				FALSE,
				label_info_id,
				flag
			);
			-- The flag is used to mark the first Org as the main contact
			if flag THEN 
				-- Update the first organization as the main contact in the form
				input_json := jsonb_set(input_json,ARRAY['organizations',counter::text,'is_main_contact'],to_jsonb(TRUE));
				flag := FALSE;
			END IF;
			--array_append(orgs_ids,organization_id)
			if organization_id is not null then
				input_json := jsonb_set(input_json,ARRAY['organizations',counter::text,'id'],to_jsonb(organization_id));
			end if;
			counter := counter + 1;
		END IF;
	END LOOP;
-- ORGANIZATIONS INFO END

-- INSPECTION
    INSERT INTO "fertiscan_0.0.18".inspection (
        inspector_id, label_info_id, sample_id, picture_set_id, inspection_comment
    ) VALUES (
        user_id, -- Assuming inspector_id is handled separately
        label_info_id,
        NULL, -- NOT handled yet
        picture_set_id,  -- Assuming picture_set_id is handled separately
		NULL
    )
    RETURNING id INTO inspection_id_value;
   
	-- Update input_json with inspection data
	input_json := jsonb_set(input_json, '{inspection_id}', to_jsonb(inspection_id_value));
	input_json := jsonb_set(input_json, '{inspection_comment}', to_jsonb(''::text));

	-- TODO: remove olap transactions from Operational transactions
	-- Update the Inspection_factual entry with the json
	UPDATE "fertiscan_0.0.18".inspection_factual
	SET original_dataset = input_json
	WHERE inspection_factual."inspection_id" = inspection_id_value;

-- INSPECTION END
	RETURN input_json;

END;
$function$;
