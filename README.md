# Auto-email

Send personalized outreach emails (with your resume attached) to a list of HR/recruiter contacts from a CSV file.

## Files

- `main.py` – reads `hr_list.csv`, builds an email from `TEMPLATE`, attaches your resume, and sends via Gmail SMTP.
- `hr_list.csv` – your contact list.
- `.env` – secrets/config (ignored by git via `.gitignore`).

## Features

- **Personalized Emails**: Uses a customizable template with AI-generated personalization lines.
- **Resume Attachment**: Automatically attaches your resume (PDF/DOCX) from a configurable path.
- **AI Integration**: Leverages OpenAI GPT to generate unique professional sentences for each email.
- **Batch Processing**: Sends emails to multiple recipients from a CSV file.
- **Success Tracking**: Counts successful sends, failures, and total execution time.
- **Rate Limiting**: Includes 15-second delays between emails to avoid spam filters.
- **Error Handling**: Logs failures and continues processing remaining emails.

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
python -m pip install pandas python-dotenv openai
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

## CSV format

`hr_list.csv` must contain these columns:

- `name`
- `company`
- `email`

Example:

```csv
name,company,email
Alex,Acme Corp,alex@acme.com
```

## Run

```powershell
python main.py
```

The script sends emails sequentially, sleeping `15` seconds between emails to reduce spam/SMTP throttling risk. At the end, it displays:
- Total emails sent successfully
- Number of failures
- Total execution time

## Customize

- Edit the email text in `main.py` under `TEMPLATE`.
- Edit short personalization lines in `main.py` under `ai_lines`.

## Safety

- Do not commit `.env` (it contains secrets). This repo already includes `.gitignore` to prevent that.
- Be mindful of email sending limits and anti-spam rules.

