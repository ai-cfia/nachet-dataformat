
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_inspection_creation()
RETURNS TRIGGER AS $$
DECLARE
    time_id UUID;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.id IS NOT NULL) AND (NEW.label_info_id IS NOT NULL) THEN
        	-- Time Dimension
            INSERT INTO "fertiscan_0.0.18".time_dimension (
                date_value, year,month,day) 
            VALUES (
                CURRENT_DATE,
                EXTRACT(YEAR FROM CURRENT_DATE),
                EXTRACT(MONTH FROM CURRENT_DATE),
                EXTRACT(DAY FROM CURRENT_DATE)	
            ) RETURNING id INTO time_id;
            -- Create the Inspection_factual entry
            INSERT INTO "fertiscan_0.0.18".inspection_factual (
                inspection_id, inspector_id, label_info_id, time_id, sample_id, picture_set_id, original_dataset
            ) VALUES (
                NEW.id,
                NEW.inspector_id,
                NEW.label_info_id,
                time_id,
                NULL, -- NOT handled yet
                NEW.picture_set_id,
                NULL
            );
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this inspection is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS inspection_creation ON "fertiscan_0.0.18".inspection;
CREATE TRIGGER inspection_creation
AFTER INSERT ON "fertiscan_0.0.18".inspection
FOR EACH ROW
EXECUTE FUNCTION olap_inspection_creation();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_inspection_update()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        IF (NEW.id IS NOT NULL) THEN
            IF (NEW.label_info_id != OLD.label_info_id) OR (NEW.inspector_id != OLD.inspector_id) OR (NEW.picture_set_id != OLD.picture_set_id) THEN
                UPDATE "fertiscan_0.0.18".inspection_factual 
                SET inspector_id = NEW.inspector_id, label_info_id = NEW.label_info_id, picture_set_id = NEW.picture_set_id
                WHERE inspection_id = NEW.id;
            END IF;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE EXCEPTION 'THE NEW ID OF THIS INSPECTION IS NULL';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS inspection_update ON "fertiscan_0.0.18".inspection;
CREATE TRIGGER inspection_update
BEFORE UPDATE ON "fertiscan_0.0.18".inspection
FOR EACH ROW
EXECUTE FUNCTION olap_inspection_update();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_inspection_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        IF (OLD.id IS NOT NULL) THEN
        DELETE FROM "fertiscan_0.0.18".inspection_factual 
        WHERE inspection_id = OLD.id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this inspection is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS inspection_deletion ON "fertiscan_0.0.18".inspection;
CREATE TRIGGER inspection_deletion
AFTER DELETE ON "fertiscan_0.0.18".inspection
FOR EACH ROW
EXECUTE FUNCTION olap_inspection_deletion();
