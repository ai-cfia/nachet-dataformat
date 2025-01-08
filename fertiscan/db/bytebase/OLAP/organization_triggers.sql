
CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_organization_information_creation()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.id IS NOT NULL) THEN
            UPDATE "fertiscan_0.0.18"."label_dimension" 
            SET organization_info_ids = array_append(organization_info_ids, NEW.id)
            WHERE label_dimension.label_id = NEW.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this organization_information is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS organization_information_creation ON "fertiscan_0.0.18".organization_information;
CREATE TRIGGER organization_information_creation
AFTER INSERT ON "fertiscan_0.0.18".organization_information
FOR EACH ROW
EXECUTE FUNCTION olap_organization_information_creation();

CREATE OR REPLACE FUNCTION "fertiscan_0.0.18".olap_organization_information_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        IF (OLD.id IS NOT NULL) THEN
            UPDATE "fertiscan_0.0.18"."label_dimension" 
            SET organization_info_ids = array_remove(organization_info_ids, OLD.id)
            WHERE label_dimension.label_id = OLD.label_id;
        ELSE
            -- Raise a warning if the condition is not met
            RAISE WARNING 'The OLAP dimension of this organization_information is not updated because the condition is not met';
        END IF;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
