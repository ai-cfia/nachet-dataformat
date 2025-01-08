
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_specification_creation()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.id IS NOT NULL) AND (NEW.label_id IS NOT NULL) THEN
        -- Update the label_dimension table with the new specification_analysis_id
        UPDATE "fertiscan_0.0.18"."label_dimension" 
        SET specification_ids = array_append(specification_ids, NEW.id)
        WHERE label_dimension.label_id = NEW.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this specification is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS specification_creation ON "fertiscan_0.0.18".specification;
CREATE TRIGGER specification_creation
AFTER INSERT ON "fertiscan_0.0.18".specification
FOR EACH ROW
EXECUTE FUNCTION olap_specification_creation();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_specification_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        IF (OLD.id IS NOT NULL) AND (OLD.label_id IS NOT NULL) THEN
        -- Update the label_dimension table with the new specification_analysis_id
        UPDATE "fertiscan_0.0.18"."label_dimension" 
        SET specification_ids = array_remove(specification_ids, OLD.id)
        WHERE label_dimension.label_id = OLD.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this specification is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS specification_deletion ON "fertiscan_0.0.18".specification;
CREATE TRIGGER specification_deletion
AFTER DELETE ON "fertiscan_0.0.18".specification
FOR EACH ROW
EXECUTE FUNCTION olap_specification_deletion();
