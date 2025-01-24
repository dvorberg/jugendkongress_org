from sqlclasses import sql

from flask import g

from . import model
from .db import cursor, commit, execute, query_one
from .email import sendmail
from .utils import process_template

field_names = {
    'address': "Adresse",
    'city': "Stadt",
    'dob': "Geburtsdatum",
    'food-preference': 'Essen',
    'gender': 'Geschlecht',
    'lactose-intolerant': "Laktose Intollerant",
    'musical-instrument': "Musikinstrument",
    'phone': "Telefonnummer",
    'remarks': "Bemerkungen",
    'ride-sharing-option': "Mitfahrgelegenheit",
    'ride-sharing-start': "ab",
    'room-mates': "Zimmerpartnerwunsch",
    'room-preference': "Zimmerwunsch",
    'zip': "Postleitzahl"}


def send_validation_mail(booking, error_dict):
    congress = g.congress

    errors = []
    for field, error in error_dict.items():
        if error is not None:
            errors.append("    • " + field_names.get(field, field))
            errors.append("      " + error)
    errors = "\n".join(errors)

    template_path = g.skin.resource_path(
        "jugendkongress/validation_email.txt")
    with open(template_path) as fp:
        template = fp.read()

    text = process_template(template, errors=errors,
                            congress=congress, booking=booking)

    sendmail("Anmeldungs Roboter", "anmeldung@jugendkongress.org",
             booking.name, booking.email,
             "Anmeldung auf jugendkongress.org vervollständigen",
             text)

def send_validation_mails():
    congress = g.congress
    bookings = model.congress.Booking.select(
        sql.where("year = %i" % congress.year),
        sql.orderby("lower(lastname), lower(firstname)"))

    for booking in bookings:
        change = booking.validate_me()
        errors = change.errors

        is_valid = True
        for error in errors.values():
            if error is not None:
                is_valid = False
                break

        if not is_valid:
            send_validation_mail(booking, errors)
