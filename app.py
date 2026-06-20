import csv
import json
import os
import smtplib
import mimetypes
import threading
import uuid
import functools
from pathlib import Path
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
from openai import OpenAI
from email_validator import validate_email, EmailNotValidError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
app.config["JSON_SORT_KEYS"] = False

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RESUME_PATH = os.getenv("RESUME_PATH")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

TEMPLATE_FILE = os.path.join(app.root_path, "email_template.txt")
SENT_LOG = os.path.join(app.root_path, "sent_emails.csv")
WRONG_LOG = os.path.join(app.root_path, "wrong_emails.csv")
ALL_SENT_LOG = os.path.join(app.root_path, "all_sent_emails.csv")
USERS_FILE = os.path.join(app.root_path, "users.json")
USER_LOGS_DIR = os.path.join(app.root_path, "user_logs")
os.makedirs(USER_LOGS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx"}

STATUS_COLUMNS = ["email", "name", "company", "sent_at", "status", "reason"]
SEND_JOBS = {}
JOB_LOCK = threading.Lock()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_log_path(user_email: str, log_type: str = "sent") -> str:
    """Get user-specific log file path (sent or wrong)."""
    safe_email = user_email.replace("@", "_").replace(".", "_")
    user_dir = os.path.join(USER_LOGS_DIR, safe_email)
    os.makedirs(user_dir, exist_ok=True)
    if log_type == "sent":
        return os.path.join(user_dir, "sent_emails.csv")
    else:
        return os.path.join(user_dir, "wrong_emails.csv")


def get_user_upload_dir(user_email: str) -> str:
    """Get user-specific upload directory."""
    safe_email = user_email.replace("@", "_").replace(".", "_")
    user_upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], safe_email)
    os.makedirs(user_upload_dir, exist_ok=True)
    return user_upload_dir


def get_resume_path(user_email: str = None):
    # Only consider resumes uploaded via the dashboard uploads folder.
    return get_uploaded_resume_path(user_email)


def get_uploaded_resume_path(user_email: str = None):
    """Get user's uploaded resume file, or search default upload folder if no user_email."""
    if user_email:
        search_dir = get_user_upload_dir(user_email)
    else:
        search_dir = app.config["UPLOAD_FOLDER"]
    
    if not os.path.exists(search_dir):
        return None
    
    for filename in os.listdir(search_dir):
        if allowed_file(filename):
            return Path(search_dir) / filename
    return None


def get_uploaded_list_path(user_email: str = None):
    """Return the first CSV file in user's upload folder, or None.
    
    This lets the dashboard show the actual uploaded CSV filename instead
    of relying on a fixed name. The send flow will also use this file.
    """
    if user_email:
        search_dir = get_user_upload_dir(user_email)
    else:
        search_dir = app.config["UPLOAD_FOLDER"]
    
    if not os.path.exists(search_dir):
        return None
    
    for filename in os.listdir(search_dir):
        if filename.lower().endswith(".csv"):
            return Path(search_dir) / filename
    return None


def read_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user_email"):
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def load_recipient_preview(list_path: Path):
    if not list_path or not list_path.exists():
        return []
    with open(list_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return [row for _, row in zip(range(5), reader)]


def is_json_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")


def update_job(job_id: str, payload: dict):
    with JOB_LOCK:
        if job_id in SEND_JOBS:
            SEND_JOBS[job_id].update(payload)


def get_job(job_id: str):
    with JOB_LOCK:
        return SEND_JOBS.get(job_id)


def execute_bulk_send_job(job_id: str, list_path: Path, template: str, subject: str, resume_path: Path, user_email: str = None):
    job = get_job(job_id)
    if not job:
        return

    update_job(job_id, {"status": "running", "started_at": datetime.utcnow().isoformat(), "progress": 0, "last_message": "Starting send job..."})
    sent_records = []
    failed_records = []

    with open(list_path, newline="", encoding="utf-8") as csvfile:
        reader = list(csv.DictReader(csvfile))
        rows = list(reader)

    total = len(rows)
    update_job(job_id, {"total": total})

    for index, row in enumerate(rows):
        email = str(row.get("email", "")).strip()
        name = get_recipient_name(row)
        sent_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        progress = int(((index + 1) / total) * 100) if total else 100

        update_job(job_id, {
            "current_email": email,
            "progress": progress,
            "current_index": index + 1,
            "last_message": f"Processing {index + 1}/{total}",
        })

        if not is_valid_email(email):
            failed_record = {
                "email": email,
                "name": name,
                "company": row.get("company", ""),
                "sent_at": sent_at,
                "status": "failed",
                "reason": "Invalid email format",
            }
            failed_records.append(failed_record)
            if user_email:
                append_log_for_user(failed_record, user_email, "wrong")
            else:
                append_log(failed_record, WRONG_LOG)
            update_job(job_id, {
                "failed_count": job.get("failed_count", 0) + 1,
                "last_message": "Skipped invalid email",
            })
            continue

        try:
            ai_line = generate_ai_line()
            body = build_email_body(template, name, ai_line)
            send_email(email, subject, body, resume_path)
            sent_record = {
                "email": email,
                "name": name,
                "company": row.get("company", ""),
                "sent_at": sent_at,
                "status": "sent",
                "reason": "",
            }
            sent_records.append(sent_record)
            if user_email:
                append_log_for_user(sent_record, user_email, "sent")
            else:
                append_log(sent_record, SENT_LOG)
            update_job(job_id, {
                "sent_count": job.get("sent_count", 0) + 1,
                "last_message": f"Sent to {email}",
            })
        except Exception as exc:
            failed_record = {
                "email": email,
                "name": name,
                "company": row.get("company", ""),
                "sent_at": sent_at,
                "status": "failed",
                "reason": str(exc),
            }
            failed_records.append(failed_record)
            if user_email:
                append_log_for_user(failed_record, user_email, "wrong")
            else:
                append_log(failed_record, WRONG_LOG)
            update_job(job_id, {
                "failed_count": job.get("failed_count", 0) + 1,
                "last_message": f"Failed: {email}",
            })

    merge_all_sent(sent_records)
    update_job(job_id, {
        "status": "completed",
        "finished_at": datetime.utcnow().isoformat(),
        "progress": 100,
        "message": f"Completed: {len(sent_records)} sent, {len(failed_records)} failed.",
    })


def load_template():
    if not os.path.exists(TEMPLATE_FILE):
        return "Dear {name},\n\n{ai_line}\n\nBest regards,\nYour Name"
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_template(content: str):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        f.write(content)


TEMPLATE_SUGGESTIONS = {
    "fresher": {
        "label": "Fresher",
        "template": "Dear {name},\n\nI recently graduated and am excited to begin my career with a company like yours. {ai_line}\n\nBest regards,\n[Your Name]",
    },
    "experienced": {
        "label": "Experienced",
        "template": "Dear {name},\n\nWith several years of experience in my field, I am eager to bring my skills to your team. {ai_line}\n\nBest regards,\n[Your Name]",
    },
    "professional": {
        "label": "Professional",
        "template": "Dear {name},\n\nI admire your company's work and would like to offer my expertise to support your next initiatives. {ai_line}\n\nBest regards,\n[Your Name]",
    },
}


def get_template_template(template_id: str) -> str | None:
    suggestion = TEMPLATE_SUGGESTIONS.get(template_id)
    return suggestion["template"] if suggestion else None


@app.route("/template-suggestions")
@login_required
def template_suggestions():
    return render_template("template_suggestions.html", suggestions=TEMPLATE_SUGGESTIONS)


@app.route("/choose-template", methods=["POST"])
@login_required
def choose_template():
    template_id = request.form.get("template_id")
    template_text = get_template_template(template_id)
    if not template_text:
        flash("Please select a valid template option.", "danger")
        return redirect(url_for("template_suggestions"))

    session["selected_template"] = template_text
    flash(f"Selected {TEMPLATE_SUGGESTIONS[template_id]['label']} template.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reset-template")
@login_required
def reset_template():
    session.pop("selected_template", None)
    flash("Template selection has been reset.", "info")
    return redirect(url_for("dashboard"))


def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if not email:
        return False
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def generate_ai_line():
    if not client:
        return "I am eager to explore how I can contribute to your team."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Write one short professional sentence about why you want to work at a technology company."
                }
            ],
            temperature=0.7,
            max_tokens=40,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "I am eager to explore how I can contribute to your team."


def send_email(to_address: str, subject: str, body: str, attachment_path: Path):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))

    mime_type, _ = mimetypes.guess_type(str(attachment_path))
    if mime_type and "/" in mime_type:
        main_type, sub_type = mime_type.split("/", 1)
    else:
        main_type, sub_type = "application", "octet-stream"

    with open(attachment_path, "rb") as f:
        part = MIMEBase(main_type, sub_type)
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=attachment_path.name)
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)


def append_log(record: dict, path: str):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=STATUS_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)


def append_log_for_user(record: dict, user_email: str, log_type: str = "sent"):
    """Append log record to user-specific log file."""
    path = get_user_log_path(user_email, log_type)
    append_log(record, path)


def merge_all_sent(records: list[dict]):
    if not records:
        return
    existing = []
    if os.path.exists(ALL_SENT_LOG):
        with open(ALL_SENT_LOG, newline="", encoding="utf-8") as csvfile:
            existing = list(csv.DictReader(csvfile))
    combined = existing + records
    with open(ALL_SENT_LOG, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(combined)


def load_status_logs(path: str):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as csvfile:
        return list(csv.DictReader(csvfile))


def load_status_logs_for_user(user_email: str, log_type: str = "sent"):
    """Load status logs for a specific user."""
    path = get_user_log_path(user_email, log_type)
    return load_status_logs(path)


def build_email_body(template: str, recipient_name: str, ai_line: str):
    return template.format(name=recipient_name, ai_line=ai_line)


def get_recipient_name(row: dict) -> str:
    for key in ["name", "Name", "full_name", "Full Name"]:
        if key in row and row[key]:
            value = str(row[key]).strip()
            if value and value.lower() not in {"nan", "none"}:
                return value
    return "Hiring Manager"


@app.route("/")
@login_required
def dashboard():
    user_email = session.get("user_email")
    email_template = session.get("selected_template", "")
    sent_log = load_status_logs_for_user(user_email, "sent")
    wrong_log = load_status_logs_for_user(user_email, "wrong")
    resume_path = get_resume_path(user_email)
    recipient_list_path = get_uploaded_list_path(user_email)
    recipient_preview = load_recipient_preview(recipient_list_path)
    return render_template(
        "dashboard.html",
        sent_count=len(sent_log),
        failed_count=len(wrong_log),
        email_template=email_template,
        sent_log=sent_log[-10:][::-1],
        wrong_log=wrong_log[-10:][::-1],
        resume_path=resume_path.name if resume_path else None,
        recipient_list_name=recipient_list_path.name if recipient_list_path else None,
        recipient_preview=recipient_preview,
        missing_config=not (EMAIL and PASSWORD),
        user_email=user_email,
    )


@app.route("/upload-list", methods=["POST"])
@login_required
def upload_list():
    user_email = session.get("user_email")
    file = request.files.get("recipient_file")
    if not file or file.filename == "":
        flash("Please upload a valid CSV file.", "danger")
        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.csv'):
        flash("Please upload a .csv file.", "danger")
        return redirect(url_for("dashboard"))

    user_upload_dir = get_user_upload_dir(user_email)
    filepath = os.path.join(user_upload_dir, filename)
    file.save(filepath)
    flash(f"Recipient list uploaded successfully: {filename}", "success")
    return redirect(url_for("dashboard"))


@app.route("/upload-resume", methods=["POST"])
@login_required
def upload_resume():
    user_email = session.get("user_email")
    file = request.files.get("resume_file")
    if not file or file.filename == "":
        flash("Please upload a PDF or DOCX resume.", "danger")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Resume must be a PDF or DOCX file.", "danger")
        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)
    user_upload_dir = get_user_upload_dir(user_email)
    filepath = os.path.join(user_upload_dir, filename)
    file.save(filepath)
    flash("Resume uploaded successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/send-bulk", methods=["POST"])
@login_required
def send_bulk():
    if not EMAIL or not PASSWORD:
        return jsonify({"error": "SMTP credentials are missing."}), 400

    user_email = session.get("user_email")
    uploaded_list = get_uploaded_list_path(user_email)
    if not uploaded_list:
        return jsonify({"error": "Please upload a recipient list first."}), 400
    list_path = str(uploaded_list)

    template = request.form.get("email_template", "").strip()
    if not template:
        template = load_template()
    write_template(template)
    subject = request.form.get("subject", "Opportunity Inquiry")
    resume_path = get_resume_path(user_email)
    if not resume_path:
        return jsonify({"error": "Resume file not found. Upload or configure RESUME_PATH."}), 400

    user_email = session.get("user_email")
    job_id = uuid.uuid4().hex
    with JOB_LOCK:
        SEND_JOBS[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "sent_count": 0,
            "failed_count": 0,
            "progress": 0,
            "current_email": None,
            "current_index": 0,
            "total": 0,
            "last_message": "Queued for sending...",
            "created_at": datetime.utcnow().isoformat(),
        }

    thread = threading.Thread(
        target=execute_bulk_send_job,
        args=(job_id, Path(list_path), template, subject, resume_path, user_email),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "status_url": url_for("job_status", job_id=job_id)})


@app.route("/api/job-status/<job_id>")
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(job)


@app.route("/download/<path:filename>")
@login_required
def download(filename):
    file_path = os.path.join(app.root_path, filename)
    if not os.path.exists(file_path):
        flash("File not found.", "danger")
        return redirect(url_for("dashboard"))
    return send_file(file_path, as_attachment=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        users = read_users()
        if email in users:
            session["user_email"] = email
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Email not registered. Please sign up first.", "danger")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("signup"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("signup"))

        users = read_users()
        if email in users:
            flash("This email is already registered. Please log in.", "warning")
            return redirect(url_for("login"))

        users[email] = {"email": email, "created_at": datetime.utcnow().isoformat()}
        save_users(users)
        session["user_email"] = email
        flash("Account created successfully. Welcome!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/api/status")
@login_required
def api_status():
    user_email = session.get("user_email")
    sent_log = load_status_logs_for_user(user_email, "sent")
    wrong_log = load_status_logs_for_user(user_email, "wrong")
    resume_path = get_resume_path(user_email)
    recipient_list_path = get_uploaded_list_path(user_email)
    return jsonify({
        "sent_count": len(sent_log),
        "failed_count": len(wrong_log),
        "recent_sent": sent_log[-10:],
        "recent_failed": wrong_log[-10:],
        "recipient_list": recipient_list_path.name if recipient_list_path else None,
        "resume_file": resume_path.name if resume_path else None,
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
