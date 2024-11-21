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

@gets_parameters_from_request
def create_booking(congress, email="", firstname=None, lastname=None):
    errors = {}

    match = email_re.match(email)
    if match is None:
        errors["email"] = "Bitte gib eine gültige e-Mail Adresse ein."
    else:
        errors["email"] = None

    if firstname is not None:
        firstname = firstname.strip()
        if firstname == "":
            errors["firstname"] = "Dieses Feld darf nicht leer sein."

    if lastname is not None:
        lastname = lastname.strip()
        if lastname == "":
            errors["lastname"] = "Dieses Feld darf nicht leer sein."

    if errors:
        return { "status": "error",
                 "errors": errors }
    else:
        return { "status": "ok",
                 "errors": errors }

    return errors

def modify_booking(congress):
    return {}
