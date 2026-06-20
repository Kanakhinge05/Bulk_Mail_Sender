# BULK MAIL SENDER

A bulk email sender application with both a CLI script and a Flask dashboard UI. Send personalized messages, attach resumes, and monitor sent/failed results from a friendly web interface.

## Files

- `app.py` – Flask web application with upload UI, email template editor, dashboard, and bulk send workflow.
- `legacy_main.py` – Original batch email script preserved for CLI use.
- `email_template.txt` – Default email template used by both the script and web app.
- `requirements.txt` – Python dependencies.
- `.env` – Secrets/config (ignored by git via `.gitignore`).
- `sent_emails.csv` – Log of emails sent in the current run.
- `wrong_emails.csv` – Log of invalid or failed emails.
- `all_sent_emails.csv` – Cumulative backup of all sent emails from all runs.
- `templates/dashboard.html` – Flask dashboard UI template.
- `uploads/` – Stores uploaded recipient list and resume files.

## Features

- **Web dashboard**: Upload recipient CSV, upload resume, edit email template, and trigger bulk sends.
- **Personalized emails**: Supports `{name}` and `{ai_line}` placeholders.
- **AI personalization**: Uses OpenAI to generate one professional sentence per email.
- **Email validation**: Validates recipient addresses before sending.
- **Attachment support**: Sends a resume PDF or DOCX with each email.
- **Send logs**: Tracks successful and failed sends in CSV logs.
- **File downloads**: Download send/failure logs directly from the dashboard.

## Prerequisites

- Python 3.9+
- A Gmail account with an **App Password** for SMTP
- OpenAI API key for AI-generated personalization

## Install

```powershell
pip install -r requirements.txt
```

## Configure

Create or update `.env`:

```env
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password
OPENAI_API_KEY=your_openai_api_key
RESUME_PATH=C:/Users/HP/My-Doc/resume.pdf
FLASK_SECRET_KEY=your_secret_key
```

Notes:
- `RESUME_PATH` is optional if you upload a resume through the dashboard.
- The app also checks `uploads/` for a resume file if `RESUME_PATH` is not set.

## Run the web dashboard

```powershell
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser.

## Make the app publicly accessible

### Option 1: Quick public URL with Ngrok (for testing)

1. Install ngrok from https://ngrok.com
2. Run the app locally:
   ```powershell
   python app.py
   ```
3. In another terminal, create a public tunnel:
   ```powershell
   ngrok http 5000
   ```
4. Share the generated public URL (e.g., `https://abc123.ngrok.io`)

### Option 2: Deploy to cloud (permanent public access)

**Recommended platforms**: Render, Railway, or Heroku

#### Deploy to Render (easiest):

1. Create a free account at https://render.com
2. Click **+ New** → **Web Service**
3. Connect your GitHub repo or paste this repo's Git URL
4. Fill in:
   - **Name**: `demo-smart-mail`
   - **Environment**: `Python 3.9`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `python app.py`
5. Add environment variables under **Environment**:
   ```
   EMAIL=your_email@gmail.com
   PASSWORD=your_gmail_app_password
   OPENAI_API_KEY=your_openai_api_key
   FLASK_SECRET_KEY=your_secret_key
   PORT=5000
   ```
6. Click **Create Web Service**
7. Your app will be live at `https://<your-app-name>.onrender.com`

#### Deploy to Railway (also easy):

1. Create account at https://railway.app
2. Click **+ New Project** → **Deploy from GitHub**
3. Select this repository
4. Add variables in **Variables** tab (same as above)
5. Your app deploys automatically to a public URL

#### Deploy to Heroku:

1. Install Heroku CLI and log in
2. Run:
   ```bash
   heroku create demo-smart-mail
   heroku config:set EMAIL=your_email@gmail.com PASSWORD=... OPENAI_API_KEY=... FLASK_SECRET_KEY=...
   git push heroku main
   ```

### Local network access

Start the app and access from another device using your PC's local IP:

```text
http://192.168.1.x:5000/
```

> ⚠️ **Security reminder**: Keep `.env` private. Do not commit credentials to Git. Use platform-provided environment variable management.

## Using the dashboard

1. Upload a recipient CSV file.
2. Upload or configure your resume file.
3. Edit the email subject and template.
4. Click **Send Emails**.

The template supports:
- `{name}` — recipient name or fallback to `Hiring Manager`
- `{ai_line}` — AI-generated personalization sentence

## CSV Format

Your uploaded CSV must include an `email` column. Optional columns:
- `name`, `Name`, `full_name`, `Full Name`
- `company`

Example:

```csv
name,company,email
Alex,Acme Corp,alex@acme.com
```

## CLI legacy script

If you prefer the original batch script, run:

```powershell
python legacy_main.py
```

This script still uses `email_template.txt`, `RESUME_PATH`, and logs to `sent_emails.csv` / `wrong_emails.csv`.

## Troubleshooting

- If app imports fail, install dependencies with `pip install -r requirements.txt`.
- Ensure Gmail SMTP credentials are correct and app passwords are enabled.
- Keep `.env` private and do not commit it.

