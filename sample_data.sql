{\rtf1\ansi\ansicpg1252\cocoartf2761
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fmodern\fcharset0 CourierNewPSMT;\f1\froman\fcharset0 Times-Roman;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\fs29\fsmilli14667 \cf0 \expnd0\expndtw0\kerning0
-- ================================\
-- Sample data\
-- ================================\
-- Users\
INSERT INTO "User"(email, first_name, last_name, phone, user_type) VALUES\
('amy.agent@acme.com','Amy','Agent','312-555-0101','agent'),\
('rob.renter@mail.com','Rob','Renter','312-555-0202','renter'),\
('rita.renter@mail.com','Rita','Renter','312-555-0303','renter');\
-- Subtypes\
INSERT INTO "Agent"(email, job_title, agency_name, agency_contact_info)\
VALUES ('amy.agent@acme.com','Senior Realtor','City Realty','ext 224');\
INSERT INTO "ProspectiveRenter"(email, desired_move_in_date,\
preferred_location, monthly_budget)\
VALUES ('rob.renter@mail.com', CURRENT_DATE + INTERVAL '30 days',\
'Downtown', 2200),\
       ('rita.renter@mail.com', CURRENT_DATE + INTERVAL '45 days', 'Near\
Campus', 1500);\
-- Addresses\
INSERT INTO "Address"(email, label, street, city, state, zip) VALUES\
('rob.renter@mail.com','Home','123 Maple St','Chicago','IL','60616'),\
('rita.renter@mail.com','Home','45 King Dr','Chicago','IL','60605');\
-- Cards\
INSERT INTO "PaymentCard"(renter_email, card_brand, card_last4, exp_month,\
exp_year, billing_address_id)\
VALUES\
('rob.renter@mail.com','Visa','4242',12,extract(year from\
CURRENT_DATE)::INT + 2,\
 (SELECT address_id FROM "Address" WHERE email='rob.renter@mail.com' LIMIT\
1)),\
('rita.renter@mail.com','Mastercard','4444',11,extract(year from\
CURRENT_DATE)::INT + 3,\
 (SELECT address_id FROM "Address" WHERE email='rita.renter@mail.com'\
LIMIT 1));\
-- Properties and subtypes\
INSERT INTO "Property Info"(type, street, city, state, zip, "Sq_Footage",\
price, description, availability) VALUES\
('apartment','200 Lake Shore Dr','Chicago','IL','60611',850,2300,'1 bed\
with lake view',TRUE),\
('house','78 Prairie Ave','Chicago','IL','60616',1600,3200,'3 bed near\
museum campus',TRUE),\
('commercial','900 W Loop','Chicago','IL','60607',2400,8500,'Retail\
shell',TRUE);\
INSERT INTO "Apartment"(property_id, "No_of_Rooms")\
VALUES ((SELECT property_id FROM "Property Info" WHERE street='200 Lake\
Shore Dr'), 3);\
INSERT INTO "House"(property_id, "No_of_Rooms")\
VALUES ((SELECT property_id FROM "Property Info" WHERE street='78 Prairie\
Ave'), 6);\
INSERT INTO "Commercial Building"(property_id, "Business_Types",\
"No_of_Rooms")\
VALUES ((SELECT property_id FROM "Property Info" WHERE street='900 W\
Loop'), 'Retail', NULL);\
-- Neighborhood one to one by property\
INSERT INTO "Neighborhood"(property_id, crime_rate, schools,\
vacation_homes, land) VALUES\
((SELECT property_id FROM "Property Info" WHERE street='200 Lake Shore\
Dr'), 5.2, 'Good', FALSE, FALSE),\
((SELECT property_id FROM "Property Info" WHERE street='78 Prairie Ave'),\
6.7, 'Average', FALSE, FALSE);\
-- Rewards registration\
INSERT INTO "Rewards_program"(renter_email) VALUES\
('rob.renter@mail.com'),\
('rita.renter@mail.com');\
-- Booking\
INSERT INTO "Bookings"(property_id, renter_email, card_id, start_date,\
end_date, total_cost, "Property_Type")\
VALUES (\
 (SELECT property_id FROM "Property Info" WHERE street='200 Lake Shore\
Dr'),\
 'rob.renter@mail.com',\
 (SELECT card_id FROM "PaymentCard" WHERE\
renter_email='rob.renter@mail.com' LIMIT 1),\
 CURRENT_DATE + 7,\
 CURRENT_DATE + 37,\
 2300,\
 'apartment' -- will be overwritten by trigger to match property\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 );
\f1\fs24 \
\pard\pardeftab720\partightenfactor0

\f0\fs29\fsmilli14667 \cf0 -- Check derived rewards count\
-- SELECT * FROM renter_rewards ORDER BY renter_email;\
}