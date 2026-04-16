# Auto-email

Send personalized outreach emails (with your resume attached) to a list of HR/recruiter contacts from a CSV file.

## Files

- `main.py` – reads `hr_list.csv`, builds an email from `TEMPLATE`, attaches your resume, and sends via Gmail SMTP.
- `hr_list.csv` – your contact list.
- `.env` – secrets/config (ignored by git via `.gitignore`).

## Prerequisites

- Python 3.9+
- A Gmail account with an **App Password** (recommended) for SMTP

## Install

```powershell
python -m pip install pandas python-dotenv
```

## Configure

Create/update `.env`:

```env
EMAIL=your_email@gmail.com
PASSWORD=your_gmail_app_password
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

The script sleeps `15` seconds between emails to reduce spam/SMTP throttling risk.

## Customize

- Edit the email text in `main.py` under `TEMPLATE`.
- Edit short personalization lines in `main.py` under `ai_lines`.

## Safety

- Do not commit `.env` (it contains secrets). This repo already includes `.gitignore` to prevent that.
- Be mindful of email sending limits and anti-spam rules.

