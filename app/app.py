from datetime import datetime, date
from decimal import Decimal
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import psycopg2

from db import get_connection, dict_cursor

app = Flask(__name__)
app.secret_key = "dev-secret-key"


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_email" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("user_type") != role:
                flash("You are not allowed to view that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def get_user(email):
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT email, first_name, last_name, phone, user_type FROM "User" WHERE email = %s',
                (email,),
            )
            return cur.fetchone()


@app.route("/")
def index():
    user_email = session.get("user_email")
    user = get_user(user_email) if user_email else None
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT property_id, type, street, city, state, zip, price, availability FROM "Property Info" WHERE availability = TRUE ORDER BY property_id DESC LIMIT 5'
            )
            properties = cur.fetchall()
    return render_template("index.html", user=user, properties=properties)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_user(email)
        if not user:
            flash("User not found. Please register first.", "danger")
            return render_template("login.html")
        session["user_email"] = user["email"]
        session["user_type"] = user["user_type"]
        flash("Logged in successfully.", "success")
        if user["user_type"] == "agent":
            return redirect(url_for("agent_dashboard"))
        return redirect(url_for("renter_dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone = request.form.get("phone")
        user_type = request.form.get("user_type")
        job_title = request.form.get("job_title")
        agency_name = request.form.get("agency_name")
        agency_contact_info = request.form.get("agency_contact_info")
        desired_move_in_date = request.form.get("desired_move_in_date")
        preferred_location = request.form.get("preferred_location")
        monthly_budget_raw = request.form.get("monthly_budget")

        if not email or not first_name or not last_name or user_type not in (
            "agent",
            "renter",
        ):
            flash("Please fill in all required fields.", "warning")
            return render_template("register.html")

        if user_type == "agent" and (not job_title or not agency_name):
            flash("Job title and agency name are required for agents.", "warning")
            return render_template("register.html")

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO "User"(email, first_name, last_name, phone, user_type) VALUES (%s, %s, %s, %s, %s)',
                        (email, first_name, last_name, phone, user_type),
                    )
                    if user_type == "agent":
                        cur.execute(
                            'INSERT INTO "Agent"(email, job_title, agency_name, agency_contact_info) VALUES (%s, %s, %s, %s)',
                            (email, job_title, agency_name, agency_contact_info),
                        )
                    else:
                        move_in_date = (
                            datetime.strptime(desired_move_in_date, "%Y-%m-%d").date()
                            if desired_move_in_date
                            else None
                        )
                        monthly_budget = (
                            Decimal(monthly_budget_raw)
                            if monthly_budget_raw
                            else None
                        )
                        cur.execute(
                            'INSERT INTO "ProspectiveRenter"(email, desired_move_in_date, preferred_location, monthly_budget) VALUES (%s, %s, %s, %s)',
                            (email, move_in_date, preferred_location, monthly_budget),
                        )
            session["user_email"] = email
            session["user_type"] = user_type
            flash("Registration successful.", "success")
            if user_type == "agent":
                return redirect(url_for("agent_dashboard"))
            return redirect(url_for("renter_dashboard"))
        except psycopg2.Error as exc:
            flash(f"Registration failed: {exc.pgerror or exc}", "danger")
    return render_template("register.html")


@app.route("/renter/dashboard")
@login_required(role="renter")
def renter_dashboard():
    email = session["user_email"]
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT * FROM "ProspectiveRenter" WHERE email = %s', (email,)
            )
            renter = cur.fetchone()
            cur.execute(
                'SELECT * FROM "Address" WHERE email = %s ORDER BY address_id',
                (email,),
            )
            addresses = cur.fetchall()
            cur.execute(
                'SELECT * FROM "PaymentCard" WHERE renter_email = %s ORDER BY card_id',
                (email,),
            )
            cards = cur.fetchall()
            cur.execute(
                "SELECT bookings_count FROM renter_rewards WHERE renter_email = %s",
                (email,),
            )
            rewards = cur.fetchone()
    return render_template(
        "renter_dashboard.html",
        renter=renter,
        addresses=addresses,
        cards=cards,
        rewards=rewards["bookings_count"] if rewards else 0,
    )


@app.route("/agent/dashboard")
@login_required(role="agent")
def agent_dashboard():
    email = session["user_email"]
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM "Agent" WHERE email = %s', (email,))
            agent = cur.fetchone()
            cur.execute('SELECT COUNT(*) FROM "Property Info"')
            property_count = cur.fetchone()["count"]
            cur.execute('SELECT COUNT(*) FROM "Bookings"')
            booking_count = cur.fetchone()["count"]
    return render_template(
        "agent_dashboard.html",
        agent=agent,
        property_count=property_count,
        booking_count=booking_count,
    )


@app.route("/addresses", methods=["GET", "POST"])
@login_required()
def addresses():
    email = session["user_email"]
    if request.method == "POST":
        label = request.form.get("label")
        street = request.form.get("street")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")
        if not street or not city:
            flash("Street and city are required.", "warning")
        else:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            'INSERT INTO "Address"(email, label, street, city, state, zip) VALUES (%s, %s, %s, %s, %s, %s)',
                            (email, label, street, city, state, zip_code),
                        )
                flash("Address added.", "success")
            except psycopg2.Error as exc:
                flash(f"Could not add address: {exc.pgerror or exc}", "danger")
        return redirect(url_for("addresses"))

    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT * FROM "Address" WHERE email = %s ORDER BY address_id',
                (email,),
            )
            addresses = cur.fetchall()
    return render_template("addresses.html", addresses=addresses)


@app.route("/addresses/<int:address_id>/delete", methods=["POST"])
@login_required()
def delete_address(address_id):
    email = session["user_email"]
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM "Address" WHERE address_id = %s AND email = %s',
                    (address_id, email),
                )
        flash("Address deleted.", "success")
    except psycopg2.Error as exc:
        flash(
            "Unable to delete address (it may be used as a billing address).",
            "danger",
        )
    return redirect(url_for("addresses"))


@app.route("/cards", methods=["GET", "POST"])
@login_required(role="renter")
def cards():
    email = session["user_email"]
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT address_id, label, street, city FROM "Address" WHERE email = %s ORDER BY address_id',
                (email,),
            )
            addresses = cur.fetchall()

    if request.method == "POST":
        card_brand = request.form.get("card_brand")
        card_last4 = request.form.get("card_last4")
        exp_month = request.form.get("exp_month")
        exp_year = request.form.get("exp_year")
        billing_address_id = request.form.get("billing_address_id")
        if not (card_brand and card_last4 and exp_month and exp_year and billing_address_id):
            flash("All card fields are required.", "warning")
        else:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            'INSERT INTO "PaymentCard"(renter_email, card_brand, card_last4, exp_month, exp_year, billing_address_id) VALUES (%s, %s, %s, %s, %s, %s)',
                            (
                                email,
                                card_brand,
                                card_last4[-4:],
                                int(exp_month),
                                int(exp_year),
                                int(billing_address_id),
                            ),
                        )
                flash("Card added.", "success")
            except psycopg2.Error as exc:
                flash(f"Could not add card: {exc.pgerror or exc}", "danger")
        return redirect(url_for("cards"))

    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT * FROM "PaymentCard" WHERE renter_email = %s ORDER BY card_id',
                (email,),
            )
            cards = cur.fetchall()
    return render_template("cards.html", cards=cards, addresses=addresses)


@app.route("/cards/<int:card_id>/delete", methods=["POST"])
@login_required(role="renter")
def delete_card(card_id):
    email = session["user_email"]
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM "PaymentCard" WHERE card_id = %s AND renter_email = %s',
                    (card_id, email),
                )
        flash("Card deleted.", "success")
    except psycopg2.Error:
        flash("Unable to delete card (it may be used in a booking).", "danger")
    return redirect(url_for("cards"))


@app.route("/search", methods=["GET", "POST"])
def search_properties():
    filters = []
    params = []
    if request.method == "POST":
        city = request.form.get("city")
        state = request.form.get("state")
        ptype = request.form.get("type")
        max_price = request.form.get("max_price")
        only_available = request.form.get("only_available")

        if city:
            filters.append("LOWER(p.city) LIKE %s")
            params.append(f"%{city.lower()}%")
        if state:
            filters.append("LOWER(p.state) LIKE %s")
            params.append(f"%{state.lower()}%")
        if ptype:
            filters.append("p.type = %s")
            params.append(ptype)
        if max_price:
            filters.append("p.price <= %s")
            params.append(Decimal(max_price))
        if only_available:
            filters.append("p.availability = TRUE")
    else:
        filters.append("p.availability = TRUE")

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""
    query = f'''
        SELECT p.property_id, p.type, p.street, p.city, p.state, p.zip, p."Sq_Footage", p.price, p.description, p.availability,
               n.crime_rate, n.schools, n.vacation_homes, n.land
        FROM "Property Info" p
        LEFT JOIN "Neighborhood" n ON n.property_id = p.property_id
        {where_clause}
        ORDER BY p.price ASC, p.property_id DESC
    '''
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(query, params)
            properties = cur.fetchall()
    return render_template("search_properties.html", properties=properties)


@app.route("/book/<int:property_id>", methods=["GET", "POST"])
@login_required(role="renter")
def book_property(property_id):
    email = session["user_email"]
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT property_id, type, street, city, state, zip, price, description, availability FROM "Property Info" WHERE property_id = %s',
                (property_id,),
            )
            property_info = cur.fetchone()
            if not property_info:
                flash("Property not found.", "danger")
                return redirect(url_for("search_properties"))

            cur.execute(
                'SELECT card_id, card_brand, card_last4 FROM "PaymentCard" WHERE renter_email = %s ORDER BY card_id',
                (email,),
            )
            cards = cur.fetchall()

    if request.method == "POST":
        start_date_raw = request.form.get("start_date")
        end_date_raw = request.form.get("end_date")
        card_id = request.form.get("card_id")
        if not (start_date_raw and end_date_raw and card_id):
            flash("All booking fields are required.", "warning")
            return redirect(url_for("book_property", property_id=property_id))

        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        if start_date >= end_date:
            flash("End date must be after start date.", "warning")
            return redirect(url_for("book_property", property_id=property_id))

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT card_id FROM "PaymentCard" WHERE card_id = %s AND renter_email = %s',
                        (int(card_id), email),
                    )
                    if not cur.fetchone():
                        flash("Select a valid payment card.", "danger")
                        return redirect(url_for("book_property", property_id=property_id))

                    cur.execute(
                        'SELECT price, type FROM "Property Info" WHERE property_id = %s',
                        (property_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        flash("Property not found.", "danger")
                        return redirect(url_for("search_properties"))

                    price, prop_type = row
                    days = (end_date - start_date).days
                    multiplier = max(days / 30, 1)
                    total_cost = Decimal(price) * Decimal(multiplier)
                    cur.execute(
                        'INSERT INTO "Bookings"(property_id, renter_email, card_id, start_date, end_date, total_cost, "Property_Type") VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (
                            property_id,
                            email,
                            int(card_id),
                            start_date,
                            end_date,
                            total_cost,
                            prop_type,
                        ),
                    )
            flash("Booking created.", "success")
            return redirect(url_for("my_bookings"))
        except psycopg2.Error as exc:
            flash(
                "Could not create booking (dates may overlap or card/property invalid).",
                "danger",
            )
    return render_template(
        "book_property.html", property=property_info, cards=cards
    )


@app.route("/my_bookings")
@login_required(role="renter")
def my_bookings():
    email = session["user_email"]
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                '''
                SELECT b.booking_id, b.start_date, b.end_date, b.total_cost, b."Property_Type",
                       p.property_id, p.street, p.city, p.state, p.zip
                FROM "Bookings" b
                JOIN "Property Info" p ON p.property_id = b.property_id
                WHERE b.renter_email = %s
                ORDER BY b.start_date DESC
                ''',
                (email,),
            )
            bookings = cur.fetchall()
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/agent/properties")
@login_required(role="agent")
def agent_properties():
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                '''
                SELECT p.property_id, p.type, p.street, p.city, p.state, p.zip, p.price, p.availability,
                       n.crime_rate, n.schools
                FROM "Property Info" p
                LEFT JOIN "Neighborhood" n ON n.property_id = p.property_id
                ORDER BY p.property_id DESC
                '''
            )
            properties = cur.fetchall()
    return render_template("agent_properties.html", properties=properties)


def _load_property(property_id):
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT * FROM "Property Info" WHERE property_id = %s',
                (property_id,),
            )
            prop = cur.fetchone()
            if not prop:
                return None
            subtype = {}
            if prop["type"] == "house":
                cur.execute(
                    'SELECT "No_of_Rooms" FROM "House" WHERE property_id = %s',
                    (property_id,),
                )
                subtype = cur.fetchone() or {}
            elif prop["type"] == "apartment":
                cur.execute(
                    'SELECT "No_of_Rooms", "Building_Type" FROM "Apartment" WHERE property_id = %s',
                    (property_id,),
                )
                subtype = cur.fetchone() or {}
            elif prop["type"] == "commercial":
                cur.execute(
                    'SELECT "Business_Types", "No_of_Rooms" FROM "Commercial Building" WHERE property_id = %s',
                    (property_id,),
                )
                subtype = cur.fetchone() or {}

            cur.execute(
                'SELECT crime_rate, schools, vacation_homes, land FROM "Neighborhood" WHERE property_id = %s',
                (property_id,),
            )
            neighborhood = cur.fetchone()
    return {"property": prop, "subtype": subtype, "neighborhood": neighborhood}


@app.route("/agent/properties/new", methods=["GET", "POST"])
@app.route("/agent/properties/<int:property_id>/edit", methods=["GET", "POST"])
@login_required(role="agent")
def agent_property_form(property_id=None):
    existing = _load_property(property_id) if property_id else None
    if property_id and not existing:
        flash("Property not found.", "danger")
        return redirect(url_for("agent_properties"))

    if request.method == "POST":
        ptype = request.form.get("type")
        street = request.form.get("street")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")
        sq_ft = request.form.get("sq_ft") or None
        price = request.form.get("price")
        description = request.form.get("description")
        availability = bool(request.form.get("availability"))
        rooms = request.form.get("rooms") or None
        building_type = request.form.get("building_type")
        business_types = request.form.get("business_types")
        crime_rate = request.form.get("crime_rate") or None
        schools = request.form.get("schools") or None
        vacation_homes = bool(request.form.get("vacation_homes"))
        land = bool(request.form.get("land"))

        if not (ptype and street and city and price):
            flash("Type, street, city, and price are required.", "warning")
            return redirect(
                url_for(
                    "agent_property_form", property_id=property_id
                )
            )

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if property_id:
                        cur.execute(
                            '''
                            UPDATE "Property Info"
                            SET type = %s, street = %s, city = %s, state = %s, zip = %s,
                                "Sq_Footage" = %s, price = %s, description = %s, availability = %s
                            WHERE property_id = %s
                            ''',
                            (
                                ptype,
                                street,
                                city,
                                state,
                                zip_code,
                                int(sq_ft) if sq_ft else None,
                                Decimal(price),
                                description,
                                availability,
                                property_id,
                            ),
                        )
                        cur.execute('DELETE FROM "House" WHERE property_id = %s', (property_id,))
                        cur.execute('DELETE FROM "Apartment" WHERE property_id = %s', (property_id,))
                        cur.execute('DELETE FROM "Commercial Building" WHERE property_id = %s', (property_id,))
                    else:
                        cur.execute(
                            '''
                            INSERT INTO "Property Info"(type, street, city, state, zip, "Sq_Footage", price, description, availability)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING property_id
                            ''',
                            (
                                ptype,
                                street,
                                city,
                                state,
                                zip_code,
                                int(sq_ft) if sq_ft else None,
                                Decimal(price),
                                description,
                                availability,
                            ),
                        )
                        property_id = cur.fetchone()[0]

                    if ptype == "house" and rooms:
                        cur.execute(
                            'INSERT INTO "House"(property_id, "No_of_Rooms") VALUES (%s, %s)',
                            (property_id, int(rooms)),
                        )
                    elif ptype == "apartment" and rooms:
                        cur.execute(
                            'INSERT INTO "Apartment"(property_id, "No_of_Rooms", "Building_Type") VALUES (%s, %s, %s)',
                            (property_id, int(rooms), building_type),
                        )
                    elif ptype == "commercial":
                        cur.execute(
                            'INSERT INTO "Commercial Building"(property_id, "Business_Types", "No_of_Rooms") VALUES (%s, %s, %s)',
                            (property_id, business_types, int(rooms) if rooms else None),
                        )

                    if any([crime_rate, schools, vacation_homes, land]):
                        cur.execute(
                            'DELETE FROM "Neighborhood" WHERE property_id = %s',
                            (property_id,),
                        )
                        cur.execute(
                            'INSERT INTO "Neighborhood"(property_id, crime_rate, schools, vacation_homes, land) VALUES (%s, %s, %s, %s, %s)',
                            (
                                property_id,
                                float(crime_rate) if crime_rate else None,
                                schools,
                                vacation_homes,
                                land,
                            ),
                        )
            flash("Property saved.", "success")
            return redirect(url_for("agent_properties"))
        except psycopg2.Error as exc:
            flash(f"Could not save property: {exc.pgerror or exc}", "danger")
            return redirect(
                url_for("agent_property_form", property_id=property_id)
            )

    context = existing or {}
    return render_template(
        "agent_property_form.html",
        property=context.get("property") if context else None,
        subtype=context.get("subtype") if context else {},
        neighborhood=context.get("neighborhood") if context else None,
    )


@app.route("/agent/properties/<int:property_id>/bookings")
@login_required(role="agent")
def agent_property_bookings(property_id):
    with get_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute(
                'SELECT property_id, street, city, state FROM "Property Info" WHERE property_id = %s',
                (property_id,),
            )
            prop = cur.fetchone()
            if not prop:
                flash("Property not found.", "danger")
                return redirect(url_for("agent_properties"))
            cur.execute(
                '''
                SELECT b.booking_id, b.start_date, b.end_date, b.total_cost,
                       u.first_name, u.last_name, b.renter_email
                FROM "Bookings" b
                JOIN "User" u ON u.email = b.renter_email
                WHERE b.property_id = %s
                ORDER BY b.start_date DESC
                ''',
                (property_id,),
            )
            bookings = cur.fetchall()
    return render_template(
        "agent_property_bookings.html", prop=prop, bookings=bookings
    )


if __name__ == "__main__":
    app.run(debug=True)
