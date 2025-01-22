##  Copyright 2024 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved.
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##
##  I have added a copy of the GPL in the file LICENSE
import re
import flask
from .utils import (gets_parameters_from_request, process_template,
                    rget, redirect)

from t4.res import email_re
from t4.passwords import random_password
from t4.sendmail import sendmail

from sqlclasses import sql

from .db import execute, query_one, insert_from_dict, commit
from .model.congress import Booking, Change, Congress

@gets_parameters_from_request
def create_booking(congress, email="", firstname=None, lastname=None,
                   checkmail=False):
    errors = {}

    match = email_re.match(email)
    if match is None:
        errors["email"] = "Bitte gib eine gültige e-Mail Adresse ein."
    else:
        count, = query_one(f"SELECT COUNT(*) FROM booking "
                           f" WHERE year = {congress.year} "
                           f"   AND email = %s", (email,))
        if count != 0:
            errors["email"] = ("Es gibt schon eine Buchung mit dieser "
                               "eMail Adresse.")
            return {"reveal-resend": True,
                    "errors": errors}

    if checkmail:
        if not "email" in errors:
            errors["email"] = None
        return { "errors": errors}

    if firstname is not None:
        firstname = firstname.strip()
        if firstname == "":
            errors["firstname"] = "Dieses Feld darf nicht leer sein."

    if lastname is not None:
        lastname = lastname.strip()
        if lastname == "":
            errors["lastname"] = "Dieses Feld darf nicht leer sein."

    if errors:
        return { "errors": errors }
    else:
        count = -1
        while count != 0:
            slug = random_password(9, use_specials=False)
            count, = query_one(f"SELECT COUNT(*) FROM booking "
                               f" WHERE year = {congress.year} "
                               f"   AND slug = %s", (slug,))

        booking = { "year": congress.year,
                    "email": email,
                    "slug": slug,
                    "firstname": firstname,
                    "lastname": lastname,
                    "user_agent": flask.request.headers.get("User-Agent")}
        insert_from_dict("booking", booking, retrieve_id=False)
        commit()

        send_booking_email(congress, Booking.from_dict(booking), True)

        return { "errors": errors,
                 "created": True,
                 "href": congress.booking_href(slug)
                }

@gets_parameters_from_request
def resend_booking_email(congress, email=None):
    booking = Booking.select_one(
        congress.where("email = ", sql.string_literal(email)))
    send_booking_email(congress, booking)

    return { "resent": True,
             "errors": {} }


def send_booking_email(congress:Congress, booking:Booking,
                       send_copy=False):
    template_path = flask.g.skin.resource_path(
        "skin/jugendkongress/booking_email.txt")
    with open(template_path) as fp:
        template = fp.read()

    if send_copy:
        bcc = [ "anmeldung@jugendkongress.org", ]
    else:
        bcc = []

    text = process_template(template, congress=congress, booking=booking)

    subject = (f"Anmeldung zum {congress.nummer} Lutherischen Jugendkongress "
               f"{congress.year}")
    sendmail("Jugendkongress Anmeldungs-Roboter",
             "anmeldung@jugendkongress.org",
             booking.name,
             booking.email,
             subject,
             text, bcc=bcc)


def modify_booking(congress, slug):
    change = Change(flask.request.form)
    Booking.validate(change)

    # The values dict will contain only fields that are explicitly
    # validated.
    values = change.validated
    values["user_agent"] = flask.request.headers.get("User-Agent")
    if (values):
        Booking.update_by_slug(congress.year, slug, **values)
        commit()

    return { "errors": change.errors }

def delete_booking(congress, slug):
    execute("DELETE FROM booking WHERE year = %s AND slug = %s",
            (congress.year, slug, ))
    commit()

    return redirect(congress.href,
                    site_message=("Deine Buchung wurde storniert. "
                                  "Am besten, du löscht auch die "
                                  "Mail, denn der Link funkioniert "
                                  "jetzt nicht mehr."),
                    site_message_class="info")

@gets_parameters_from_request
def select_workshop(congress, slug, workshop_id):
    execute("INSERT INTO workshop_choices "
            "( SELECT id, %s FROM booking WHERE year = %s AND slug = %s)"
            "    ON CONFLICT DO NOTHING",
            ( workshop_id, congress.year, slug))
    commit()
    return { "selected": workshop_id }

@gets_parameters_from_request
def drop_workshop(congress, slug, workshop_id):
    execute("DELETE FROM workshop_choices "
            " WHERE workshop_id = %s"
            "   AND booking_id = (SELECT id FROM booking "
            "                      WHERE year = %s AND slug = %s)",
            (workshop_id, congress.year, slug))
    commit()

    return { "selected": [] }
