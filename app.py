from flask import Flask, render_template, request, redirect, jsonify, session
import sqlite3

app = Flask(__name__)
app.secret_key = "bookbazaar_secret_key"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect("books.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():

    conn = get_db()

    # USERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # BOOKS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price INTEGER NOT NULL,
            condition TEXT NOT NULL,
            seller_id INTEGER
        )
    """)

    # ORDERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            book_title TEXT NOT NULL,
            price INTEGER NOT NULL,
            buyer_name TEXT NOT NULL,
            buyer_phone TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    conn = get_db()

    books = conn.execute("""
        SELECT * FROM books
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        books=books
    )


# =========================
# SELL BOOK
# =========================

@app.route("/sell", methods=["POST"])
def sell():

    if not session.get("user_id"):
        return redirect("/login")

    title = request.form["title"]
    author = request.form["author"]
    price = request.form["price"]
    condition = request.form["condition"]

    seller_id = session["user_id"]

    conn = get_db()

    conn.execute("""
        INSERT INTO books
        (
            title,
            author,
            price,
            condition,
            seller_id
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        title,
        author,
        price,
        condition,
        seller_id
    ))

    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# BUY BOOK
# =========================

@app.route("/buy", methods=["POST"])
def buy():

    data = request.get_json()

    book_id = data.get("book_id")
    book_title = data.get("book_title")
    price = data.get("price")
    buyer_name = data.get("buyer_name")
    buyer_phone = data.get("buyer_phone")

    if not buyer_name or not buyer_phone:

        return jsonify({
            "success": False,
            "message": "Name aur phone number required hai."
        })

    conn = get_db()

    conn.execute("""
        INSERT INTO orders
        (
            book_id,
            book_title,
            price,
            buyer_name,
            buyer_phone
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        book_id,
        book_title,
        price,
        buyer_name,
        buyer_phone
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Order successfully placed!"
    })


# =========================
# ORDERS
# =========================

@app.route("/orders")
def orders():

    conn = get_db()

    orders = conn.execute("""
        SELECT * FROM orders
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "orders.html",
        orders=orders
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                password
            ))

            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            conn.close()

            return "Email already registered!"

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            password
        )).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect("/")

        return "Invalid email or password!"

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# PROFILE + MY BOOKS
# =========================

@app.route("/profile")
def profile():

    if not session.get("user_id"):
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()

    books = conn.execute("""
        SELECT *
        FROM books
        WHERE seller_id = ?
        ORDER BY id DESC
    """, (
        user_id,
    )).fetchall()

    conn.close()

    return render_template(
        "profile.html",
        books=books
    )


# =========================
# AI RECOMMENDATION
# =========================

@app.route("/ai", methods=["POST"])
def ai():

    data = request.get_json()

    question = data.get(
        "question",
        ""
    ).lower()

    conn = get_db()

    books = conn.execute("""
        SELECT * FROM books
    """).fetchall()

    conn.close()

    if not books:

        return jsonify({
            "answer":
            "Abhi marketplace mein koi book available nahi hai."
        })

    budget = None
    numbers = []

    for word in question.replace(
        "₹",
        " "
    ).split():

        try:
            numbers.append(int(word))

        except ValueError:
            pass

    if numbers:
        budget = max(numbers)

    results = []
    keywords = question.split()

    for book in books:

        title = book["title"].lower()
        author = book["author"].lower()

        if any(
            word in title or word in author
            for word in keywords
            if len(word) > 2
        ):

            if (
                budget is None
                or book["price"] <= budget
            ):

                results.append(book)

    if results:

        answer = "🤖 BookBazaar AI recommends:\n\n"

        for book in results[:5]:

            answer += (
                f"📚 {book['title']}\n"
                f"Author: {book['author']}\n"
                f"Price: ₹{book['price']}\n"
                f"Condition: {book['condition']}\n\n"
            )

    else:

        answer = (
            "🤖 Mujhe exact matching book nahi mili.\n\n"
            "Try karo:\n"
            "• Python book\n"
            "• DBMS under 400\n"
            "• Mathematics book"
        )

    return jsonify({
        "answer": answer
    })


# =========================
# START
# =========================

if __name__ == "__main__":

    create_table()

    app.run(debug=True)