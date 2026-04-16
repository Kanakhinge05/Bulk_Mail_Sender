import pandas as pd
import smtplib
import time
import os
import random
import mimetypes
from pathlib import Path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def resolve_resume_path():
    env_path = os.getenv("RESUME_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if candidate.exists() and candidate.is_file():
            return candidate
        raise FileNotFoundError(f"RESUME_PATH points to missing file: {candidate}")

    candidates = [
        "resume.pdf",
        "Resume.pdf",
        "resume.docx",
        "Resume.docx",
        "cv.pdf",
        "CV.pdf",
        "cv.docx",
        "CV.docx",
    ]
    for name in candidates:
        candidate = Path.cwd() / name
        if candidate.exists() and candidate.is_file():
            return candidate

    return None

resume_path = resolve_resume_path()
if resume_path is None:
    raise SystemExit(
        "Resume file not found. Put `resume.pdf` in this folder or set `RESUME_PATH` in your environment."
    )

# Load CSV file
df = pd.read_csv(r"c:\Users\HP\My-Doc\hr_list.csv")

# Email template
TEMPLATE = """
Dear Hiring Team,

I hope you are doing well.

I am reaching out to express my interest in potential opportunities within your organization for roles such as AWS DevOps Engineer, Junior DevOps Engineer, or Cloud Engineer. I am currently working as a DevOps Engineer at Vected Technologies, where I have gained hands-on experience with AWS services (EC2, S3, IAM, VPC), Terraform, and CI/CD pipelines using GitHub Actions.

I am particularly interested in contributing to teams that focus on scalable infrastructure, automation, and modern DevOps practices. I am eager to further develop my skills in areas such as Kubernetes and advanced cloud architecture while delivering reliable and efficient solutions.

I have attached my resume for your review. I would greatly appreciate the opportunity to discuss how my skills and experience align with your team’s needs.

Thank you for your time and consideration.

Best regards,
Kanak Kumar Hinge
Phone Number: 8602343454
LinkedIn Profile: https://www.linkedin.com/in/kanakkumarhinge/


{ai_line}


"""

ai_lines = [
    "I admire your company's innovation and growth.",
    "I am excited about the impactful work your team is doing.",
    "Your organization's vision aligns with my skills and interests.",
]

# Generate AI line
def generate_ai_line():
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Write one short professional sentence about why you want to work at a tech company"}
        ]
    )
    return response.choices[0].message.content.strip()

# Send email
def send_email(to_email, subject, body, attachment_path: Path):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to_email

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
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=attachment_path.name,
    )
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

# Loop through list
for index, row in df.iterrows():
    try:
        ai_line = random.choice(ai_lines)

        body = TEMPLATE.format(
            ai_line=ai_line
        )

        send_email(row["email"], "Application for DevOps Role", body, resume_path)

        print(f"✅ Sent to {row['email']}")
        time.sleep(15)  # delay to avoid spam

    except Exception as e:
        print(f"❌ Failed for {row['email']}:", e)
