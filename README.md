# Real Estate Management Application

CS 425 Database Organization - Fall 2025

This project implements a Real Estate Management system backed by a fully normalized PostgreSQL schema. It includes an ER model, relational schema, sample data population scripts, and a complete Flask web application wired to the database.

This project focuses on database design first and application functionality second. The UI is minimal for now. Team members can improve the styling and navigation later.

---

## Project Structure

```
/
├── schema/
│   ├── schema.sql           # Full PostgreSQL schema
│   ├── sample_data.sql      # Sample dataset
│   ├── er-model.pdf         # ER diagram
│
├── app/
│   ├── app.py               # Flask application
│   ├── db.py                # Database helper
│   ├── requirements.txt     # Python dependencies
│   ├── templates/           # Jinja HTML templates
│   └── static/              # Optional CSS or assets
│
└── README.md                # ReadMe file
```

---

## 1. Database Setup

Before running the Flask application, you must create and load the PostgreSQL database.

### Create the database:

```bash
createdb realestate_db
```

### Run the schema:

```bash
psql -d realestate_db -f schema/schema.sql
```

### Load sample data:

```bash
psql -d realestate_db -f schema/sample_data.sql
```

This creates all tables, triggers, constraints, and inserts sample records for testing.

---

## 2. Running the Flask Application

Go into the `app/` directory:

```bash
cd app
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start the server:

```bash
python app.py
```

Visit the application in your browser:

```
http://127.0.0.1:5000
```

---

## 3. Application Features

### Renter Features

* Register as a renter
* Manage personal addresses
* Manage saved payment cards
* Search available properties with filters
* Book properties using stored payment cards
* View and cancel bookings
* Automatically earn rewards counts through the database view

### Agent Features

* Register as an agent
* View all listed properties
* Add or edit property listings (with corresponding subtype tables)
* View bookings for any property
* Delete property listings when no bookings conflict with them

### Login System

Simple login using only email and user type (agent or renter). No password is required for this course project.

---

## 4. Database Interests and Constraints

This project showcases several advanced database features:

* Schemas with search_path
* Trigger based attribute consistency
* Exclusion constraints to prevent overlapping bookings
* One to one relationships (Neighborhood, subtype tables)
* Foreign keys with ON DELETE behavior
* Materialized logic through a view (rewards count)

These are all exercised automatically through the sample data and app behavior.

---

## 5. Editing and Improving the UI

The current UI uses basic Bootstrap and Jinja templates. Teammates working on UIUX can freely:

* Edit files in `app/templates/`
* Add CSS to `app/static/`
* Improve layout in `base.html`
* Add better navigation
* Redesign pages without touching backend logic

None of these changes affect the database layer.

---

## 6. Known Good Workflow for Teammates

1. Clone or pull the repo
2. Set up the PostgreSQL database
3. Start Flask locally
4. Test renter and agent flows
5. Update templates as needed
6. Commit UI changes only

No team member needs to modify the SQL files unless adding new features.

---

## 7. Authors

* Members: Shree, Numa, Sakina
* Course: CS 425 Database Organization
* Instructor: Yousef Elmehdwi
* Semester: Fall 2025

---

## 8. Video Demo (to be added)

A short demonstration video will be added before final submission showing:

* Database running
* App startup
* Renter workflow
* Agent workflow

---

## 9. Notes

If you get database connection errors, update credentials in:

```
app/db.py
```

Adjust:

```python
user="your_username"
password="your_password_if_any"
```

Everything else should work out of the box.
