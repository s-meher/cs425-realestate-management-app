-- CS 425 Real Estate Management
-- Reset
DROP SCHEMA IF EXISTS realestate CASCADE;
CREATE SCHEMA realestate;
SET search_path = realestate, public;

-- Needed for the no overlap booking rule
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ================================
-- User and subtypes (disjoint)
-- ================================
CREATE TABLE "User" (
    email VARCHAR(200) PRIMARY KEY,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,
    phone VARCHAR(30),
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('agent','renter'))
);
CREATE INDEX idx_user_email ON "User"(email);

-- Agent subtype (key is email per ERD)
CREATE TABLE "Agent" (
    email VARCHAR(200) PRIMARY KEY REFERENCES "User"(email) ON DELETE CASCADE,
    job_title VARCHAR(100) NOT NULL,
    agency_name VARCHAR(150) NOT NULL,
    agency_contact_info VARCHAR(200)
);

-- ProspectiveRenter subtype (key is email per ERD)
CREATE TABLE "ProspectiveRenter" (
    email VARCHAR(200) PRIMARY KEY REFERENCES "User"(email) ON DELETE CASCADE,
    desired_move_in_date DATE,
    preferred_location VARCHAR(100),
    monthly_budget NUMERIC(12,2) CHECK (monthly_budget >= 0)
);

-- Keep user_type aligned with subtypes and disjoint
CREATE OR REPLACE FUNCTION enforce_user_types() RETURNS trigger AS $$
BEGIN
    IF NEW.user_type = 'agent' THEN
        IF NOT EXISTS (SELECT 1 FROM "Agent" a WHERE a.email = NEW.email) THEN
            RAISE EXCEPTION 'Agent must have Agent row';
        END IF;
        IF EXISTS (SELECT 1 FROM "ProspectiveRenter" r WHERE r.email = NEW.email) THEN
            RAISE EXCEPTION 'User cannot be both agent and renter';
        END IF;
    ELSIF NEW.user_type = 'renter' THEN
        IF NOT EXISTS (SELECT 1 FROM "ProspectiveRenter" r WHERE r.email = NEW.email) THEN
            RAISE EXCEPTION 'Renter must have ProspectiveRenter row';
        END IF;
        IF EXISTS (SELECT 1 FROM "Agent" a WHERE a.email = NEW.email) THEN
            RAISE EXCEPTION 'User cannot be both agent and renter';
        END IF;
    END IF;
    RETURN NEW;
END$$ LANGUAGE plpgsql;

-- Only enforce subtype rule when user_type changes after insert
CREATE TRIGGER trg_user_types_after
AFTER UPDATE OF user_type ON "User"
FOR EACH ROW EXECUTE FUNCTION enforce_user_types();

-- In the phase 2 design we also had triggers on Agent and ProspectiveRenter.
-- They are commented out here so that initial data loading is possible.
-- CREATE TRIGGER trg_agent_after
-- AFTER INSERT ON "Agent"
-- FOR EACH ROW EXECUTE FUNCTION enforce_user_types();

-- CREATE TRIGGER trg_renter_after
-- AFTER INSERT ON "ProspectiveRenter"
-- FOR EACH ROW EXECUTE FUNCTION enforce_user_types();

-- ================================
-- Address (owned by User)
-- ================================
CREATE TABLE "Address" (
    address_id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL REFERENCES "User"(email) ON DELETE CASCADE,
    label VARCHAR(80),
    street VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    zip VARCHAR(20)
);
CREATE INDEX idx_address_user ON "Address"(email);

-- ================================
-- PaymentCard (for ProspectiveRenter) with Billing Address
-- ================================
CREATE TABLE "PaymentCard" (
    card_id SERIAL PRIMARY KEY,
    renter_email VARCHAR(200) NOT NULL REFERENCES "ProspectiveRenter"(email) ON DELETE CASCADE,
    card_brand VARCHAR(30) NOT NULL,
    card_last4 CHAR(4) NOT NULL,
    exp_month INT NOT NULL CHECK (exp_month BETWEEN 1 AND 12),
    -- Simple lower bound on expiration year to avoid using CURRENT_DATE in a CHECK
    exp_year INT NOT NULL CHECK (exp_year >= 2024),
    billing_address_id INT NOT NULL REFERENCES "Address"(address_id) ON DELETE RESTRICT,
    UNIQUE (renter_email, card_brand, card_last4, exp_month, exp_year)
);
CREATE INDEX idx_card_renter ON "PaymentCard"(renter_email);

-- ================================
-- Property Info and subtypes
-- ================================
CREATE TABLE "Property Info" (
    property_id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL CHECK (type IN ('house','apartment','commercial','vacation_home','land')),
    street VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    zip VARCHAR(20),
    "Sq_Footage" INT CHECK ("Sq_Footage" IS NULL OR "Sq_Footage" > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    description TEXT,
    availability BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_property_city_state ON "Property Info"(city, state);
CREATE INDEX idx_property_type ON "Property Info"(type);

-- House
CREATE TABLE "House" (
    property_id INT PRIMARY KEY REFERENCES "Property Info"(property_id) ON DELETE CASCADE,
    "No_of_Rooms" INT NOT NULL CHECK ("No_of_Rooms" > 0)
);

-- Apartment
CREATE TABLE "Apartment" (
    property_id INT PRIMARY KEY REFERENCES "Property Info"(property_id) ON DELETE CASCADE,
    "No_of_Rooms" INT NOT NULL CHECK ("No_of_Rooms" > 0),
    "Building_Type" VARCHAR(100)
);

-- Commercial Building
CREATE TABLE "Commercial Building" (
    property_id INT PRIMARY KEY REFERENCES "Property Info"(property_id) ON DELETE CASCADE,
    "Business_Types" VARCHAR(100) NOT NULL,
    "No_of_Rooms" INT
);

-- ================================
-- Neighborhood (PK is Property_ID per ERD)
-- one to one with Property
-- ================================
CREATE TABLE "Neighborhood" (
    property_id INT PRIMARY KEY REFERENCES "Property Info"(property_id) ON DELETE CASCADE,
    crime_rate REAL,
    schools VARCHAR(200),
    vacation_homes BOOLEAN,
    land BOOLEAN
);

-- ================================
-- Bookings
-- includes Property Type attribute per ERD
-- ================================
CREATE TABLE "Bookings" (
    booking_id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES "Property Info"(property_id) ON DELETE RESTRICT,
    renter_email VARCHAR(200) NOT NULL REFERENCES "ProspectiveRenter"(email) ON DELETE RESTRICT,
    card_id INT NOT NULL REFERENCES "PaymentCard"(card_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_cost NUMERIC(12,2) NOT NULL CHECK (total_cost >= 0),
    "Property_Type" VARCHAR(20) NOT NULL,
    CHECK (start_date < end_date)
);

-- Keep Property_Type in sync with Property Info
CREATE OR REPLACE FUNCTION set_booking_property_type() RETURNS trigger AS $$
DECLARE
    t varchar(20);
BEGIN
    SELECT type INTO t FROM "Property Info" p WHERE p.property_id = NEW.property_id;
    IF t IS NULL THEN
        RAISE EXCEPTION 'Property not found';
    END IF;
    NEW."Property_Type" := t;
    RETURN NEW;
END$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bookings_set_type
BEFORE INSERT OR UPDATE OF property_id ON "Bookings"
FOR EACH ROW EXECUTE FUNCTION set_booking_property_type();

-- Prevent overlapping bookings on same property
ALTER TABLE "Bookings"
    ADD COLUMN stay daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]')) STORED;

ALTER TABLE "Bookings"
    ADD CONSTRAINT no_overlap_per_property
    EXCLUDE USING gist (
        property_id WITH =,
        stay WITH &&
    );

-- Card must belong to the same renter
-- This version from the design uses a subquery, which is not allowed in a CHECK in Postgres.
-- We keep it here commented as documentation of the design intent.
-- ALTER TABLE "Bookings"
--     ADD CONSTRAINT card_belongs_to_renter
--     CHECK (EXISTS (
--         SELECT 1 FROM "PaymentCard" c
--         WHERE c.card_id = card_id AND c.renter_email = renter_email
--     ));

CREATE INDEX idx_bookings_renter ON "Bookings"(renter_email);
CREATE INDEX idx_bookings_property ON "Bookings"(property_id);

-- Optional: mark availability false once booked
CREATE OR REPLACE FUNCTION mark_unavailable_after_booking() RETURNS trigger AS $$
BEGIN
    UPDATE "Property Info" SET availability = FALSE WHERE property_id = NEW.property_id;
    RETURN NEW;
END$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mark_unavailable
AFTER INSERT ON "Bookings"
FOR EACH ROW EXECUTE FUNCTION mark_unavailable_after_booking();

-- ================================
-- Rewards_program (registration) + derived count(Bookings)
-- matches ERD idea: count of bookings
-- ================================
CREATE TABLE "Rewards_program" (
    renter_email VARCHAR(200) PRIMARY KEY REFERENCES "ProspectiveRenter"(email) ON DELETE CASCADE,
    registered_on DATE NOT NULL DEFAULT CURRENT_DATE
);

-- Derived count of bookings for registered renters
CREATE VIEW renter_rewards AS
SELECT rp.renter_email,
       COUNT(b.booking_id)::INT AS bookings_count
FROM "Rewards_program" rp
LEFT JOIN "Bookings" b ON b.renter_email = rp.renter_email
GROUP BY rp.renter_email;
