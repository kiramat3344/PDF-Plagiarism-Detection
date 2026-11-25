

########################################################################

import threading
import uuid
import random
import smtplib
from functools import wraps
from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, send_file
import os
import pymupdf
import sqlite3
import time


from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Store live comparison progress
comparison_jobs = {}

app.secret_key = "pdf_project_secret_key_2026"
EMAIL_ADDRESS = "whbus5706@gmail.com"
EMAIL_PASSWORD = "igsk cxwm spzi twhp"

UPLOAD_FOLDER = "uploads"
DATABASE_FOLDER = "database"
REPORT_FOLDER = "reports"

DATABASE = os.path.join(DATABASE_FOLDER, "history.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)



# Create Database
def create_database():

    connection = sqlite3.connect(DATABASE)

    # Existing Results Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file1 TEXT,
            file2 TEXT,
            similarity REAL,
            status TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Users Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Add user_id to existing results table
    columns = connection.execute(
        "PRAGMA table_info(results)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "user_id" not in column_names:
        connection.execute(
            "ALTER TABLE results ADD COLUMN user_id INTEGER"
        )

    connection.commit()
    connection.close()


create_database()

def send_otp_email(receiver_email, otp):
    subject = "PDF Checker - Password Reset OTP"

    message = f"""
Your OTP for password reset is:

{otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.
"""

    email_text = f"Subject: {subject}\n\n{message}"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(
            EMAIL_ADDRESS,
            receiver_email,
            email_text.encode("utf-8")
        )
        server.quit()
        return True

    except Exception as e:
        print("Email Error:", e)
        return False



# Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if len(password) < 8:
            return render_template(
                "signup.html",
                error="Password must be at least 8 characters."
            )

        hashed_password = generate_password_hash(password)

        try:
            connection = sqlite3.connect(DATABASE)

            connection.execute("""
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            """, (username, email, hashed_password))

            connection.commit()
            connection.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            return render_template(
                "signup.html",
                error="Username or Email already exists."
            )

    return render_template("signup.html")
#forget password
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        connection = sqlite3.connect(DATABASE)
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user:

            otp = str(random.randint(100000, 999999))

            if send_otp_email(email, otp):

                session["reset_email"] = email
                session["reset_otp"] = otp
                session["otp_expiry"] = time.time() + 300

                return redirect(url_for("verify_otp"))

            return "Email could not be sent. Please try again."

        return "Email not registered!"

    return render_template("forgot_password.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if "reset_email" not in session:
        return redirect(url_for("forgot_password"))

    if request.method == "POST":

        entered_otp = request.form["otp"]

        if time.time() > session.get("otp_expiry", 0):
            session.pop("reset_otp", None)
            session.pop("otp_expiry", None)
            return "OTP expired! Please request a new OTP."

        if entered_otp == session.get("reset_otp"):

            session["otp_verified"] = True

            return redirect(url_for("reset_password"))

        return "Invalid OTP! Please try again."

    return render_template("verify_otp.html")


    
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if not session.get("otp_verified") or not session.get("reset_email"):
        return redirect(url_for("forgot_password"))

    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if len(password) < 8:
            return "Password must be at least 8 characters!"

        if password != confirm_password:
            return "Passwords do not match!"

        hashed_password = generate_password_hash(password)

        connection = sqlite3.connect(DATABASE)

        connection.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (hashed_password, session["reset_email"])
        )

        connection.commit()
        connection.close()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("otp_expiry", None)
        session.pop("otp_verified", None)

        return redirect(url_for("login"))

    return render_template("reset_password.html")


# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"], password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# Login Required
def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper

# Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# Home Page
@app.route("/")
@login_required
def home():
    return render_template("index.html")


# History Page
@app.route("/history-page")
@login_required
def history_page():
    return render_template("history.html")



# Background PDF Comparison Function

def run_pdf_comparison(job_id, documents, user_id):

    total = len(documents) * (len(documents) - 1) // 2

    comparison_jobs[job_id]["total"] = total

    results = []

    connection = sqlite3.connect(DATABASE)

    try:
        texts = [doc["text"] for doc in documents]

        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform(texts)

        completed = 0

        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):

                percentage = round(
                    float(vectors[i].multiply(vectors[j]).sum()) * 100,
                    2
                )

                status = (
                    "High Similarity"
                    if percentage >= 30
                    else "Low Similarity"
                )

                cursor = connection.execute(
                    """
                    INSERT INTO results
                    (file1, file2, similarity, status, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        documents[i]["name"],
                        documents[j]["name"],
                        percentage,
                        status,
                        user_id
                    )
                )

                results.append({
                    "id": cursor.lastrowid,
                    "file1": documents[i]["name"],
                    "file2": documents[j]["name"],
                    "similarity": percentage,
                    "status": status
                })

                completed += 1

                comparison_jobs[job_id]["completed"] = completed

        connection.commit()

        comparison_jobs[job_id]["results"] = results
        comparison_jobs[job_id]["status"] = "completed"

    except Exception as e:

        connection.rollback()

        comparison_jobs[job_id]["status"] = "error"
        comparison_jobs[job_id]["message"] = str(e)

    finally:
        connection.close()


# Upload and Compare PDFs

@app.route("/upload", methods=["POST"])
@login_required
def upload_files():

    files = [
        f for f in request.files.getlist("pdfFiles")
        if f.filename.strip()
    ]

    if len(files) > 50:
        return jsonify({
            "message": "Maximum 50 PDF files are allowed."
        }), 400

    if len(files) < 2:
        return jsonify({
            "message": "Please upload at least 2 PDFs."
        }), 400

    documents = []

    for file in files:

        if not file.filename.lower().endswith(".pdf"):
            continue

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(path)

        try:
            pdf = pymupdf.open(path)
            text = ""

            for page in pdf:
                text += page.get_text()

            pdf.close()

            if text.strip():
                documents.append({
                    "name": filename,
                    "text": text
                })

        except Exception:
            continue

    if len(documents) < 2:
        return jsonify({
            "message": "Please upload at least 2 valid text-based PDFs."
        }), 400

    job_id = str(uuid.uuid4())

    comparison_jobs[job_id] = {
        "user_id": session["user_id"],
        "completed": 0,
        "total": len(documents) * (len(documents) - 1) // 2,
        "status": "processing",
        "results": []
    }

    thread = threading.Thread(
        target=run_pdf_comparison,
        args=(job_id, documents, session["user_id"]),
        daemon=True
    )

    thread.start()

    return jsonify({
        "job_id": job_id,
        "message": "Comparison started!"
    })


# Get Live Comparison Progress

@app.route("/progress/<job_id>")
@login_required
def get_progress(job_id):

    job = comparison_jobs.get(job_id)

    if not job or job["user_id"] != session["user_id"]:
        return jsonify({
            "message": "Job not found."
        }), 404

    return jsonify({
        "completed": job["completed"],
        "total": job["total"],
        "status": job["status"],
        "results": job["results"],
        "message": job.get("message", "")
    })



# Get Comparison History
@app.route("/history")
@login_required
def history():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    records = connection.execute(
        "SELECT * FROM results WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return jsonify([dict(record) for record in records])


# Delete Comparison History

@app.route("/delete-history/<int:record_id>", methods=["DELETE"])
@login_required
def delete_history(record_id):

    connection = sqlite3.connect(DATABASE)

    cursor = connection.execute(
        "DELETE FROM results WHERE id = ? AND user_id = ?",
        (record_id, session["user_id"])
    )

    connection.commit()

    deleted = cursor.rowcount

    connection.close()

    if deleted == 0:
        return jsonify({
            "message": "Record not found"
        }), 404

    return jsonify({
        "message": "Record deleted successfully!"
    })




# Download Professional PDF Report
@app.route("/download-report/<int:report_id>")
@login_required
def download_report(report_id):

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    record = connection.execute(
        "SELECT * FROM results WHERE id = ? AND user_id = ?",
       (report_id, session["user_id"])
    ).fetchone()

    connection.close()

    if record is None:
        return "Report not found", 404

    filename = f"report_{report_id}.pdf"
    filepath = os.path.join(REPORT_FOLDER, filename)

    pdf = canvas.Canvas(filepath)

    # Header
    pdf.setFillColorRGB(0.1, 0.2, 0.4)
    pdf.rect(0, 740, 600, 100, fill=1)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, 790, "PDF SIMILARITY REPORT")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 765, "PDF Plagiarism Detection System")

    # Report Information
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 700, "Comparison Details")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, 660, f"Report ID: {record['id']}")
    pdf.drawString(50, 630, f"First PDF: {record['file1']}")
    pdf.drawString(50, 600, f"Second PDF: {record['file2']}")

    # Similarity Box
    pdf.setFillColorRGB(0.9, 0.95, 1)
    pdf.roundRect(50, 490, 480, 75, 10, fill=1)

    pdf.setFillColorRGB(0.1, 0.2, 0.4)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(70, 535, "Similarity Percentage")

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(70, 505, f"{record['similarity']}%")

    # Status
    pdf.setFillColorRGB(0, 0.5, 0)
    if record['status'] == "High Similarity":
        pdf.setFillColorRGB(0.8, 0, 0)

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 450, f"Status: {record['status']}")

    # Date
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 410, f"Comparison Date: {record['date']}")

    # Footer
    pdf.setStrokeColorRGB(0.7, 0.7, 0.7)
    pdf.line(50, 100, 550, 100)

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(
        50, 80,
        "Note: Similarity does not prove plagiarism."
    )

    pdf.setFont("Helvetica", 9)
    pdf.drawString(50, 55, "Generated by PDF Plagiarism Detection System")

    pdf.save()

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename
    )


# Dashboard Statistics

@app.route("/dashboard-stats")
@login_required
def dashboard_stats():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    stats = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'High Similarity'
                THEN 1 ELSE 0 END) AS high_count,
            SUM(CASE WHEN status = 'Low Similarity'
                THEN 1 ELSE 0 END) AS low_count,
            AVG(similarity) AS average
        FROM results
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    connection.close()

    return jsonify({
        "total": stats["total"] or 0,
        "high": stats["high_count"] or 0,
        "low": stats["low_count"] or 0,
        "average": round(stats["average"] or 0, 2)
    })



@app.route("/clear-history", methods=["DELETE"])
@login_required
def clear_history():
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        "DELETE FROM results WHERE user_id = ?",
        (session["user_id"],)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "message": "All history deleted successfully!"
    })

@app.route("/comparison-details/<int:record_id>")
@login_required
def comparison_details(record_id):

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    record = connection.execute(
        "SELECT * FROM results WHERE id = ? AND user_id = ?",
        (record_id, session["user_id"])
    ).fetchone()

    connection.close()

    if record is None:
        return "Comparison record not found", 404

    return render_template(
        "details.html",
        record=record
    )


if __name__ == "__main__":
    app.run(debug=True)
