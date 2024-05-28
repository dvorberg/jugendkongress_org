import sys, os, os.path as op, string, subprocess, tempfile

from t4.sendmail import sendmail
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

def sendmail_template(template_filename,
                      from_name, from_email,
                      to_name, to_email,
                      subject, fields,
                      attachments=[], headers={}, bcc=[]):

    # Load the template.
    path = op.join(config["EMAIL_TEMPLATE_PATH"], template_filename)
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

    if "roboter" in from_name.lower():
        bcc.append("roboter-kopie@bluetenlese-gottesdienste.de")

    sendmail(from_name, from_email,
             to_name, to_email,
             subject,
             message,
             multipart_subtype="alternative",
             headers=headers, bcc=bcc)

    if debug:
        # This should be a logger, of course.
        print(f"Mail sent to {to_name} ‹{to_email}›", file=sys.stderr)


def get_info_from(kw):
    if "user" in kw:
        user = kw["user"]
        firstname = user.firstname
        lastname = user.lastname
        email = user.email

    if "gottesdienst_id" in kw:
        gottesdienst_id = kw["gottesdienst_id"]

        gottesdienst_date_o = datum_nach_id(gottesdienst_id)
        gottesdienst_datum = pretty_german_date(gottesdienst_date_o,
                                                monthname=True)

    ret = locals().copy()
    ret.update(kw)
    return ret

def notify_team(what, **kw):
    info = get_info_from(kw)
    headers = {}
    bcc = []
    if what == "predigt_uebernommen":
        subject = ("Predigt übernommen: {firstname} {lastname} "
                   "am {gottesdienst_datum} ({kurzname})")
        f = formataddr(("{firstname} {lastname}".format(**info),
                        info["email"]))
        headers["Reply-To"] = f
        if not debug: headers["Cc"] = f
    elif what == "predigt_zurueckgegeben":
        subject = "Predigt zurückgegeben am {gottesdienst_datum} ({kurzname})"
    else:
        raise ValueError(what)

    sendmail_template(
        what + ".html",
        "Blütenlese Benachrichtigungs Roboter",
        "benachrichtigungs-roboter@bluetenlese-gottesdienst.de",
        "Blütenlese Team",
        "bluetenlesegottesdienste@selk.de",
        subject, info, headers=headers, bcc=bcc)


def involved_as_html(involved):
    lines = ["<div><b>Am Gottesdienst sind laut Datenbank beteilig:</b></div>"]
    for user in involved:
        role = user.role.capitalize()
        lines.append(f"<div>"
                     f"<b>{role}:</b> {user.firstname} {user.lastname} "
                     f"‹{user.email}› {user.phone}"
                     f"</div>")
    return "\n".join(lines)

def notify_involved(what, gottesdienst_id, **kw):
    kw["gottesdienst_id"] = gottesdienst_id
    info = get_info_from(kw)
    involved = Involved.bei_gottesdienst(gottesdienst_id)
    info["involved"] = involved_as_html(involved)

    headers = {}
    bcc = []
    if what == "kalender_comment_changed":
        subject = "blgd Kommentar ({gottesdienst_datum}): {kalender_comment}"
        user = authentication.get_user()
        headers["Reply-To"] = formataddr( ("%s %s" % ( user.firstname,
                                                       user.lastname, ),
                                           user.email) )
    else:
        raise ValueError(what)

    for recipient in involved:
        info["recipient"] = recipient

        sendmail_template(
            what + ".html",
            "Blütenlese Benachrichtigungs Roboter",
            "benachrichtigungs-roboter@bluetenlese-gottesdienst.de",
            f"{recipient.firstname} {recipient.lastname}",
            recipient.email,
            subject, info, headers=headers, bcc=bcc)
