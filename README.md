# Smart Mail Sender

Send personalized outreach emails (with your resume attached) to a list of HR/recruiter contacts from a CSV file.

## Files

- `main.py` – Main script that processes the CSV, validates emails, builds emails from template, attaches resume, and sends via Gmail SMTP.
- `hr_list.csv` – Your contact list (located at `c:\Users\HP\My-Doc\hr_list.csv`).
- `email_template.txt` – Customizable email template.
- `requirements.txt` – Python dependencies.
- `.env` – Secrets/config (ignored by git via `.gitignore`).
- `sent_emails.csv` – Log of emails sent in the current run.
- `wrong_emails.csv` – Log of invalid or failed emails.
- `all_sent_emails.csv` – Cumulative backup of all sent emails from all runs.

## Features

- **Personalized Emails**: Uses recipient name from CSV (falls back to "Hiring Manager") and AI-generated personalization lines.
- **Email Validation**: Validates email format and domain using `email-validator` library.
- **Resume Attachment**: Automatically attaches your resume (PDF/DOCX) from a configurable path.
- **AI Integration**: Leverages OpenAI GPT to generate unique professional sentences for each email.
- **Batch Processing**: Sends emails to multiple recipients from a CSV file.
- **Error Handling & Logging**: Logs successful sends, format invalidations, and send failures to CSV files.
- **Cumulative Backup**: Maintains a history of all sent emails across runs.
- **Success Tracking**: Counts successful sends, failures, and total execution time (displayed in minutes if >=60 seconds).
- **Rate Limiting**: Includes 15-second delays between emails to avoid spam filters.

## Architecture Diagram

```text
+---------------------+
|   Config File       |
| (Recipients, Msg)   |
+----------+----------+
           |
           v
+---------------------+
|   Python Script     |
|  (SmartMail Sender) |
+----------+----------+
           |
           v
+---------------------+
|     SMTP Server     |
| (e.g., Gmail SMTP)  |
+----------+----------+
           |
           v
+---------------------+
|   Recipient Inbox   |
+---------------------+
```

## Prerequisites

- Python 3.9+
- A Gmail account with an **App Password** (recommended) for SMTP
- OpenAI API key for AI-generated personalization

## Install

```powershell
pip install -r requirements.txt
```

## Configure

Create/update `.env`:

```env
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password
OPENAI_API_KEY=your_openai_api_key
RESUME_PATH=C:/Users/HP/My-Doc/resumes/KK_resume.pdf
```

Notes:
- `RESUME_PATH` can be absolute or relative to this project folder.
- If you don’t set `RESUME_PATH`, `main.py` looks for common filenames like `resume.pdf` in the project directory.

## CSV Format

`hr_list.csv` must contain at least an `email` column. Optional columns for personalization:

- `name` (or `Name`, `full_name`, `Full Name`) – Used for greeting (e.g., "Dear John")
- Other columns are preserved in logs.

Example:

```csv
name,company,email
Alex,Acme Corp,alex@acme.com
```

## Run

```powershell
python main.py
```

The script validates emails, sends sequentially with 15-second delays, and logs results. Output includes:
- Total emails sent successfully
- Number of failures
- Total execution time

## Customize

- Edit the email text in `email_template.txt` (placeholders: `{name}` for recipient, `{ai_line}` for AI text).
- Edit short personalization lines in `main.py` under `ai_lines`.
- Modify validation or logging logic in `main.py` as needed.

## Safety

- Do not commit `.env` (it contains secrets). This repo already includes `.gitignore` to prevent that.
- Be mindful of email sending limits and anti-spam rules.
- Invalid emails are skipped and logged to avoid wasting sends.

