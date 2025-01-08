CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".new_specification(
humidity FLOAT,
ph FLOAT,
solubility FLOAT,
language "fertiscan_0.0.18".language,
label_id UUID,
edited BOOLEAN = FALSE
)
RETURNS uuid 
LANGUAGE plpgsql
AS $function$
DECLARE
    specification_id uuid;
    record RECORD;
    _id uuid;
BEGIN
	-- CHECK IF ANY OF THE INPUTS ARE NOT NULL 
	IF COALESCE(humidity, ph, solubility) IS NULL THEN
		RAISE EXCEPTION 'ALL of the input parameters are null';
	END IF;
	INSERT INTO specification (humidity, ph, solubility, edited,LANGUAGE,label_id)
			VALUES (
				humidity,
				ph,
				solubility,
				edited,
				language,
				label_id
			)
            RETURNING id INTO specification_id;
    RETURN specification_id;
END;
$function$;
