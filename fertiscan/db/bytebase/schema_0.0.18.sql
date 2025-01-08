--Schema creation "fertiscan_0.0.18"
DO
$do$
BEGIN
IF (EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'fertiscan_0.0.18')) THEN

drop schema "fertiscan_0.0.18" Cascade;	
create schema "fertiscan_0.0.18";
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    CREATE TABLE "fertiscan_0.0.18"."users" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "email" text NOT NULL UNIQUE,
    "registration_date" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp
    );

    -- CREATE A TYPE FOR FRENCH/ENGLISH LANGUAGE
    CREATE TYPE "fertiscan_0.0.18".LANGUAGE AS ENUM ('fr', 'en');

    CREATE TABLE "fertiscan_0.0.18"."picture_set" (
    "id" uuid NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    "picture_set" json NOT NULL,
    "owner_id" uuid NOT NULL REFERENCES "fertiscan_0.0.18".users(id),
    "upload_date" date NOT NULL DEFAULT current_timestamp,
    "name" text
    );
        
    alter table "fertiscan_0.0.18".users ADD "default_set_id" uuid REFERENCES "fertiscan_0.0.18".picture_set(id);

    CREATE TABLE "fertiscan_0.0.18"."picture" (
    "id" uuid NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    "picture" json NOT NULL,
    "nb_obj" int,
    "picture_set_id" uuid NOT NULL REFERENCES "fertiscan_0.0.18".picture_set(id),
    "verified" boolean NOT NULL DEFAULT false,
    "upload_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE "fertiscan_0.0.18"."province" (
    "id" SERIAL PRIMARY KEY,
    "name" text UNIQUE NOT NULL
    );

    CREATE TABLE "fertiscan_0.0.18"."region" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "province_id" int REFERENCES "fertiscan_0.0.18".province(id),
    "name" text NOT NULL
    );

    CREATE TABLE "fertiscan_0.0.18"."unit" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "unit" text NOT NULL,
    "to_si_unit" float
    );

    CREATE TABLE "fertiscan_0.0.18"."element_compound" (
    "id" SERIAL PRIMARY KEY,
    "number" int NOT NULL,
    "name_fr" text NOT NULL,
    "name_en" text NOT NULL,
    "symbol" text NOT NULL UNIQUE
    );

    CREATE TABLE "fertiscan_0.0.18"."label_information" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "product_name" text,
    "lot_number" text,
    "npk" text,
    "n" float,
    "p" float,
    "k" float,
    "guaranteed_title_en" text,
    "guaranteed_title_fr" text,
    "title_is_minimal" boolean,
    "record_keeping" boolean
    );
    
    CREATE TABLE "fertiscan_0.0.18"."label_dimension" (
    "label_id" uuid PRIMARY KEY,
    "organization_info_ids" uuid[] DEFAULT '{}',
    "instructions_ids" uuid[] DEFAULT '{}',
    "cautions_ids" uuid[] DEFAULT '{}',
    "first_aid_ids" uuid[] DEFAULT '{}',
    "warranties_ids" uuid[] DEFAULT '{}',
    "specification_ids" uuid[] DEFAULT '{}',
    "ingredient_ids" uuid[] DEFAULT '{}',
    "micronutrient_ids" uuid[] DEFAULT '{}',
    "guaranteed_ids" uuid[] DEFAULT '{}',
    "registration_number_ids" uuid[] DEFAULT '{}',
    "weight_ids" uuid[] DEFAULT '{}',
    "volume_ids" uuid[] DEFAULT '{}',
    "density_ids" uuid[] DEFAULT '{}'
    );

    CREATE TABLE "fertiscan_0.0.18"."time_dimension" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "date_value" date,
    "year" int,
    "month" int,
    "day" int,
    "month_name" text,
    "day_name" text
    );

    CREATE TABLE "fertiscan_0.0.18"."inspection_factual" (
    "inspection_id" uuid PRIMARY KEY,
    "inspector_id" uuid ,
    "label_info_id" uuid ,
    "time_id" uuid REFERENCES "fertiscan_0.0.18".time_dimension(id),
    "sample_id" uuid,
    "picture_set_id" uuid,
    "inspection_date" timestamp DEFAULT CURRENT_TIMESTAMP,
    "original_dataset" json
    );

    CREATE TABLE "fertiscan_0.0.18"."organization_information" (
        "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        "name" text,
        "website" text,
        "phone_number" text,
        "address" text,
        "edited" boolean DEFAULT false,
        "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
        "is_main_contact" boolean DEFAULT false NOT NULL,
        CONSTRAINT check_not_all_null CHECK (
            (name IS NOT NULL)::integer +
            (website IS NOT NULL)::integer +
            (phone_number IS NOT NULL)::integer +
            (address IS NOT NULL)::integer >= 1)
    );
   
   
    CREATE TABLE "fertiscan_0.0.18"."location" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name" text,
    "address" text NOT NULL,
    "address_number" text,
    "city" text,
    "postal_code" text,
    "region_id" uuid REFERENCES "fertiscan_0.0.18".region(id)
    );    
   
    CREATE TABLE "fertiscan_0.0.18"."organization" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name" text UNIQUE NOT NULL,
    "website" text,
    "phone_number" text,
    "address" text,
    "main_location_id" uuid REFERENCES "fertiscan_0.0.18".location(id),
    "upload_date" timestamp DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp DEFAULT CURRENT_TIMESTAMP
    );
   
    Alter table "fertiscan_0.0.18".location ADD "organization_id" uuid REFERENCES "fertiscan_0.0.18".organization(id);

    CREATE TABLE "fertiscan_0.0.18"."sample" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "number" uuid,
    "collection_date" date,
    "location" uuid REFERENCES "fertiscan_0.0.18".location(id)
    );
   
    CREATE TYPE "fertiscan_0.0.18".metric_type as ENUM ('volume', 'weight','density');

    CREATE TABLE "fertiscan_0.0.18"."metric" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "value" float,
    "edited" boolean,
    "unit_id" uuid REFERENCES "fertiscan_0.0.18".unit(id),
    "metric_type" "fertiscan_0.0.18".metric_type,
    "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    CONSTRAINT check_not_all_null CHECK (
        (value IS NOT NULL)::integer +
        (unit_id IS NOT NULL)::integer >= 1)
    );

    CREATE TABLE "fertiscan_0.0.18"."sub_type" (
        "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        "type_fr" text Unique NOT NULL,
        "type_en" text unique NOT NULL
    );

    CREATE TABLE "fertiscan_0.0.18"."registration_number_information" (
        "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        "identifier" text NOT NULL,
        "name" text,
        "is_an_ingredient" BOOLEAN,
        "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
        "edited" BOOLEAN DEFAULT FALSE
    );

    CREATE TABLE "fertiscan_0.0.18"."specification" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "humidity" float,
    "ph" float,
    "solubility" float,
    "edited" boolean,
    "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    "language" "fertiscan_0.0.18".LANGUAGE
    );

    CREATE TABLE "fertiscan_0.0.18"."sub_label" (
        "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        "text_content_fr" text NOT NULL DEFAULT '',
        "text_content_en" text NOT NULL DEFAULT '',
        "label_id" uuid NOT NULL REFERENCES "fertiscan_0.0.18"."label_information" ("id") ON DELETE CASCADE,
        "edited" boolean, --this is because with the current upsert we can not determine if it was edited or not
        "sub_type_id" uuid NOT NULL REFERENCES "fertiscan_0.0.18"."sub_type" ("id"),
        CONSTRAINT check_not_all_null CHECK (
            (COALESCE(sub_label.text_content_en, '') <> '') OR
            (COALESCE(sub_label.text_content_fr, '') <> '')
        )
    );

    CREATE TABLE "fertiscan_0.0.18"."micronutrient" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "read_name" text,
    "value" float,
    "unit" text ,
    "element_id" int REFERENCES "fertiscan_0.0.18".element_compound(id),
    "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    "edited" boolean,
    "language" "fertiscan_0.0.18".LANGUAGE
    );

    CREATE TABLE "fertiscan_0.0.18"."guaranteed" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "read_name" text,
    "value" float ,
    "unit" text ,
    "language" "fertiscan_0.0.18".LANGUAGE,
    "element_id" int REFERENCES "fertiscan_0.0.18".element_compound(id),
    "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    "edited" boolean,
    CONSTRAINT check_not_all_null CHECK (
        (read_name IS NOT NULL)::integer +
        (value IS NOT NULL)::integer +
        (unit IS NOT NULL)::integer >= 1)
    );

    CREATE TABLE "fertiscan_0.0.18"."ingredient" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "organic" boolean,
    "active" boolean,
    "name" text,
    "value" float,
    "unit" text,
    "edited" boolean,
    "label_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    "language" "fertiscan_0.0.18".LANGUAGE
    );

    CREATE TABLE "fertiscan_0.0.18"."inspection" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "verified" boolean DEFAULT false,
    "upload_date" timestamp DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    "inspector_id" uuid NOT NULL REFERENCES "fertiscan_0.0.18".users(id),
    "label_info_id" uuid REFERENCES "fertiscan_0.0.18".label_information(id) ON DELETE CASCADE,
    "sample_id" uuid REFERENCES "fertiscan_0.0.18".sample(id),
    "picture_set_id" uuid REFERENCES "fertiscan_0.0.18".picture_set(id),
    "inspection_comment" text,
    "verified_date" timestamp default null
    );

    CREATE TABLE "fertiscan_0.0.18"."fertilizer" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name" text UNIQUE NOT NULL,
    "registration_number" text,
    "upload_date" timestamp DEFAULT CURRENT_TIMESTAMP,
    "update_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    "latest_inspection_id" uuid REFERENCES "fertiscan_0.0.18".inspection(id) ON DELETE SET NULL,
    "main_contact_id" uuid REFERENCES "fertiscan_0.0.18".organization(id) ON DELETE SET NULL 
    );-- It should actually try to seek if there are any other organization that can be found under the latest_inspection organisation_information instead of setting it to null

    Alter table "fertiscan_0.0.18".inspection ADD "fertilizer_id" uuid REFERENCES "fertiscan_0.0.18".fertilizer(id);

    -- Trigger function for the `user` table
    CREATE OR REPLACE FUNCTION update_user_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger for the `user` table
    CREATE TRIGGER user_update_before
    BEFORE UPDATE ON  "fertiscan_0.0.18".users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_timestamp();

    -- Trigger function for the `analysis` table
    CREATE OR REPLACE FUNCTION update_analysis_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger for the `analysis` table
    CREATE TRIGGER analysis_update_before
    BEFORE UPDATE ON  "fertiscan_0.0.18".inspection
    FOR EACH ROW
    EXECUTE FUNCTION update_analysis_timestamp();

    -- Trigger function for the `fertilizer` table
    CREATE OR REPLACE FUNCTION update_fertilizer_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
    NEW.update_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger for the `fertilizer` table
    CREATE TRIGGER fertilizer_update_before
    BEFORE UPDATE ON  "fertiscan_0.0.18".fertilizer
    FOR EACH ROW
    EXECUTE FUNCTION update_fertilizer_timestamp();

    -- Trigger function for the `organization` table
    CREATE OR REPLACE FUNCTION update_organization_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger for the `organization` table
    CREATE TRIGGER organization_update_before
    BEFORE UPDATE ON  "fertiscan_0.0.18".organization
    FOR EACH ROW
    EXECUTE FUNCTION update_organization_timestamp();

    -- Trigger function for the `inspection` table
    CREATE OR REPLACE FUNCTION update_inspection_original_dataset_protection()
    RETURNS TRIGGER AS $$
    BEGIN
    IF (TG_OP = 'UPDATE') AND (OLD.original_dataset IS NULL) THEN
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') AND (OLD.original_dataset IS NOT NULL) THEN
        -- Protect the original dataset from being updated
        NEW.original_dataset = OLD.original_dataset;
        RETURN NEW;
    END IF;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger for the `inspection` table
    CREATE TRIGGER inspection_update_protect_original_dataset
    BEFORE UPDATE ON  "fertiscan_0.0.18".inspection_factual
    FOR EACH ROW
    EXECUTE FUNCTION update_inspection_original_dataset_protection();

    -- Insert the default types : [instruction, caution,first_aid, warranty]
    INSERT INTO "fertiscan_0.0.18".sub_type(type_fr,type_en) VALUES
    ('instructions','instructions'),
    ('mises_en_garde','cautions');
 --   ('premier_soin','first_aid'), -- We are not using this anymore
 --   ('garanties','warranties'); -- we are not using this anymore
end if;
END
$do$;
