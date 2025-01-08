CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".get_label_info_json(
label_id uuid)
RETURNS jsonb 
LANGUAGE plpgsql
AS $function$
DECLARE
    record RECORD;
    verified_bool BOOLEAN = FALSE;
BEGIN
    SELECT 
        id,
        product_name,
        lot_number, 
        npk, 
        n, 
        p, 
        k,
        record_keeping
    INTO 
        record
    FROM 
        label_information
    WHERE 
        id = label_id
    LIMIT 1; 
    IF record IS NULL THEN
        RAISE WARNING 'No record found for label_id: %', label_id;
        RETURN NULL;
    END IF;
    SELECT 
        verified
    INTO
        verified_bool
    FROM
        inspection
    WHERE
        label_info_id = label_id
    LIMIT 1; 
    RETURN jsonb_build_object(
        'label_id', record.id,
        'name', record.product_name,
        'k', record.k,
        'n', record.n,
        'p', record.p,
        'npk', record.npk,
        'lot_number', record.lot_number,
        'verified', verified_bool,
        'record_keeping', record.record_keeping
    );
END;
$function$;
