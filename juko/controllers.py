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

import flask
from .utils import gets_parameters_from_request

from t4.res import email_re
from t4.passwords import random_password

from sqlclasses import sql

from .db import execute, query_one, insert_from_dict, commit
from .model.congress import Booking

@gets_parameters_from_request
def create_booking(congress, email="", firstname=None, lastname=None,
                   checkmail=False):
    errors = {}

    match = email_re.match(email)
    if match is None:
        errors["email"] = "Bitte gib eine gültige e-Mail Adresse ein."
    else:
        count, = query_one(f"SELECT COUNT(*) FROM booking "
                           f" WHERE congress_year = {congress.year} "
                           f"   AND email = %s", (email,))
        if count != 0:
            errors["email"] = ("Es gibt schon eine Buchung mit dieser "
                               "eMail Adresse.")
            return {"reveal-resend": True,
                    "errors": errors}

    if checkmail:
        return { "errors": { "email": None }}

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
                               f" WHERE congress_year = {congress.year} "
                               f"   AND slug = %s", (slug,))

        booking = { "congress_year": congress.year,
                    "email": email,
                    "slug": slug,
                    "firstname": firstname,
                    "lastname": lastname, }
        insert_from_dict("booking", booking, retrieve_id=False)
        commit()

        send_booking_email(Booking.from_dict(booking))

        return { "errors": errors,
                 "created": True,
                 "href": congress.booking_href(slug)
                }

@gets_parameters_from_request
def resend_welcome(congress, email=None):
    booking = Booking.select_one(
        congress.where("email = ", sql.string_literal(email)))
    send_booking_email(booking)

    return { "resent": True,
             "errors": {} }


def send_booking_email(booking:Booking):
    pass

def modify_booking(congress):
    return {}
