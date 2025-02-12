import sys, os, os.path as op, string, subprocess, tempfile

from t4.sendmail import sendmail as t4_sendmail
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from t4.typography import pretty_german_date

from . import debug, config, authentication

def lynx_dump(html):
    with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".html") as fp:
        fp.write(html)
        fp.flush()

        state = subprocess.run("lynx -dump -nomargins " + fp.name,
                               shell=True,
                               capture_output=True,
                               check=True)
        return state.stdout.decode("utf-8", "ignore")

def sendmail(from_name, from_email,
             to_name, to_email,
             subject, message, attachments=[], headers={}, bcc=[],
             text_subtype="plain", encoding="utf-8", multipart_subtype="mixed"):
    if debug:
        to_name = "Diedrich Vorberg"
        to_email = "diedrich@tux4web.de"

        if "Cc" in headers:
            print("Cc not used:", headers["Cc"])
            del headers["Cc"]

        t4_sendmail(from_name, from_email,
                    to_name, to_email,
                    subject, message, attachments, headers, bcc,
                    text_subtype, encoding, multipart_subtype)

    if debug:
        # This should be a logger, of course.
        print(f"Mail sent to {to_name} ‹{to_email}›", file=sys.stderr)

def sendmail_template(template_filename,
                      from_name, from_email,
                      to_name, to_email,
                      subject, fields,
                      attachments=[], headers={}, bcc=[]):

    # Load the template.
    path = op.join(config["SKIN_PATH"], template_filename)
    with open(path) as fp:
        template = fp.read()

    if template_filename.endswith(".html"):
        message = MIMEMultipart("related")

        # Execute the template using the mapping “fields” provided.
        message_html = template.format(**fields)
        message_txt = lynx_dump(message_html)

        text_parts = MIMEMultipart("alternative")
        message.attach(text_parts)

        text_parts.attach(MIMEText(message_txt, "plain", "utf-8"))
        text_parts.attach(MIMEText(message_html, "html", "utf-8"))
    elif template_filename.endswith(".txt"):
        message = template.format(**fields)

    if not "Reply-To" in headers:
        user = authentication.get_user()

        if user.email:
            headers["Reply-To"] = formataddr(
                (f"{user.firstname} {user.lastname}", user.email,))

    if debug:
        to_name = "Diedrich Vorberg"
        to_email = "diedrich@tux4web.de"

        if "Cc" in headers:
            print("Cc not used:", headers["Cc"])
            del headers["Cc"]

    if "%(" in subject: subject = subject % fields
    if "{" in subject: subject = subject.format(**fields)

    sendmail(from_name, from_email,
             to_name, to_email,
             subject,
             message,
             multipart_subtype="alternative",
             headers=headers, bcc=bcc)
