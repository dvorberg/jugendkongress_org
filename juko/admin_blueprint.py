##  Copyright 2024–25 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved
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

import re, string, datetime

from flask import Blueprint, g, request, session, abort, redirect, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized

from ll.xist import xsc
from ll.xist.ns import html

from t4 import sql
from t4.res import login_re, email_re
from t4.passwords import apple_style_random_password, password_good_enough

from .form_feedback import FormFeedback, NullFeedback
from .db import Result, cursor, commit, execute
from .email import sendmail_template

from . import authentication, model
from .utils import (get_site_url, gets_parameters_from_request, redirect,
                    rget, rchecked, OrderByHandler)
from .ptutils import js_string_literal


bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/login.py", methods=('GET', 'POST'))
@gets_parameters_from_request
def login(login=None, password=None, redirect_to=None,
          description=None, alert_class=None):
    if rget("description") or rget("alert_class"):
        # The description will be put into the output HTML verbatimly
        # and must not come from the request.
        raise ValueError()

    template = g.skin.load_template("skin/admin/login.pt")

    if request.method == "POST":
        feedback = FormFeedback()

        if not login:
            feedback.give("login", "Bitte füllen Sie dieses Feld aus.")
        if not password:
            feedback.give("password", "Bitte füllen Sie dieses Feld aus.")

        if feedback.is_valid():
            try:
                authentication.login(login, password)
            except Unauthorized:
                msg = "Unbekannter Benutzer oder falsches Passwort."
                feedback.give("login", msg)
                feedback.give("password", msg)

        if feedback.is_valid():
            if redirect_to is None:
                # For our very template this has to be done here.
                # template.extra_builtins["user"] = authentication.get_user()
                return redirect("/admin/bookings.py")
            else:
                return redirect(redirect_to)
    else:
        feedback = NullFeedback()

    ret = template(feedback=feedback, redirect_to=redirect_to,
                   description=description, alert_class=alert_class)

    response = make_response(ret, 200)
    response.headers["Pragma"] = "no-cache"
    return response


@bp.route("/logout.py")
@authentication.login_required
def logout():
    authentication.logout()
    return redirect(get_site_url(site_message="Sie wurden ausgeloggt."))

@bp.route("/forgott.py", methods=('GET', 'POST'))
@gets_parameters_from_request
def forgott(login=None):
    template = g.skin.load_template("skin/admin/forgott.pt")

    if request.method == "POST":
        feedback = FormFeedback()
        email_match = login_match = None

        if not login:
            feedback.give("login", "Bitte füllen Sie dieses Feld aus.")
        else:
            email_match = email_re.match(login)
            login_match = login_re.match(login)

            if email_match is None and login_match is None:
                feedback.give(
                    "login", "Kein gültiges Login oder e-Mail Adresse.")

        if feedback.is_valid():
            if email_match is not None:
                where = sql.where("lower(email) = ",
                                  sql.string_literal(login.lower()))
            elif login_match is not None:
                where = sql.where("login = ", sql.string_literal(login))
            else:
                raise ValueError(login)

            dbuser = model.users.User.select_one(where)
            if dbuser is None:
                feedback.give("login", "Benutzer nicht gefunden.")
            else:
                send_forgotten_email(dbuser)
                return template(sent=True)
    else:
        feedback = NullFeedback()

    return template(feedback=feedback, sent=False)

def send_forgotten_email(dbuser):
    with cursor() as cc:
        # Clean the request table.
        cc.execute("DELETE FROM forgotten_password_requests "
                   "      WHERE user_login = %s"
                   "         OR ctime + '4 hours'::interval < NOW()",
                   (dbuser.login,) )

        # Create the new entry.
        slug = apple_style_random_password(4, 6)
        cc.execute("INSERT INTO forgotten_password_requests"
                   "            (user_login, slug)"
                   "     VALUES (%s, %s)",
                   (dbuser.login, slug,) )
        commit()

        # Send the email
        site_url = g.skin.site_url
        link = "%s/admin/reset_password.py/%s" % ( site_url, slug, )

        login = dbuser.login
        firstname = dbuser.firstname
        lastname = dbuser.lastname

        sendmail_template( "admin/forgotten_email.txt",
                           "Jugendkongress Webmaster",
                           "webmaster@jugendkongress.org",
                           "%s %s" % ( firstname, lastname, ), dbuser.email,
                           "Passwort-Anfrage auf jugendkongress.org", locals() )

password_strength_error_message = """\
Das Passwort ist nicht stark genug. Das Passwort muss enthalten:
Großbuchstaben, Kleinbuchstaben, eine Ziffer und ein
Sonderzeichen. Wenn eines von den vieren fehlt, meckert der Computer.
"""

@bp.route("/reset_password.py/<slug>", methods=("GET", "POST",))
@gets_parameters_from_request
def reset_password(slug, password1=None, password2=None):
    template = g.skin.load_template("skin/admin/reset_password.pt")

    with cursor() as cc:
        # Remove stale links.
        cc.execute("DELETE FROM forgotten_password_requests "
                   "      WHERE ctime + '4 hours'::interval < NOW()")
        commit()

        cc.execute("SELECT user_login FROM forgotten_password_requests "
                   " WHERE slug = %s", ( slug, ))
        tpl = cc.fetchone()
        if tpl is None:
            msg = "Ungültiger Passwort-Link (älter als vier Stunden?)"
            return redirect(get_site_url(site_message=msg))
        else:
            user_login, = tpl

    if request.method == "POST":
        feedback = FormFeedback()
        if password1 != password2:
            feedback.give("password1", "Die Passwörter stimme nicht überein.")
        else:
            if not password_good_enough(password1):
                feedback.give(
                    "password1", password_strength_error_message)

        if feedback.is_valid():
            password = generate_password_hash(password1)

            with cursor() as cc:
                cc.execute("UPDATE users SET password = %s "
                           " WHERE login = %s", ( password, user_login, ))
                commit()

            return redirect(get_site_url() + "/admin/login.py")
    else:
        feedback = NullFeedback()

    return template(feedback=feedback, user_login=user_login)

@bp.route("/users.py", methods=("POST", "GET"))
@authentication.login_required
def users():
    template = g.skin.load_template("skin/admin/users.pt")

    def delete_onclick(user):
        tmpl = ('return confirm("Möchten Sie den Eintrag von " + '
                '%s + " " + %s + " löschen?")')
        return tmpl % ( js_string_literal(user.firstname),
                        js_string_literal(user.lastname), )

    users = model.users.User.select(sql.orderby("login"))

    return template(users=users, delete_onclick=delete_onclick)

@bp.route("/delete.py")
@gets_parameters_from_request
@authentication.login_required
def delete(login):
    if login == authentication.get_user().login:
        raise ValueError("Dude! You can’t delete yourself.")

    user = model.users.User.select_one(
        sql.where("login =", sql.string_literal(login)))

    # query_one("SELECT * FROM user_info WHERE login = %s" ,
    #                 (login,),
    #                 authentication.User)

    with cursor() as cc:
        cc.execute("DELETE FROM users WHERE login = %s", ( user.login, ))
        commit()

    return redirect("/admin/users.py",
                    site_message="Der Eintrag von %s %s wurde gelöscht." % (
                        user.firstname, user.lastname,))

@bp.route("/delete_user_password.py")
@authentication.login_required
@gets_parameters_from_request
def delete_user_password(login):
    if login == authentication.get_user().login:
        raise ValueError("Dude! You can’t delete yourself.")

    user = model.users.User.select_one(
        sql.where("login =", sql.string_literal(login)))

    with cursor() as cc:
        cc.execute("UPDATE users SET password = NULL "
                   " WHERE login = %s", ( user.login, ))
        commit()

    return redirect("/admin/users.py",
                    site_message="Das Passwort von %s %s wurde gelöscht." % (
                        user.firstname, user.lastname,))

@bp.route("/user_form.py", methods=("POST", "GET"))
@authentication.login_required
@gets_parameters_from_request
def user_form(request_login=None, feedback:FormFeedback=None):
    current_user = authentication.get_user()

    # Security precautions.
    #if not current_user.is_root \
    #   and not current_user.has_role("User Manager") \
    #   or request_login is None:
    #    request_login = current_user.login

    if feedback is None:
        feedback = NullFeedback()

    if request_login == "__new":
        user = model.users.User.empty()
    else:
        user = model.users.User.select_one(
            sql.where("login = ",
                      sql.string_literal(request_login)))

    template = g.skin.load_template("skin/admin/user_form.pt")
    return template(dbuser=user,
                    feedback=feedback,
                    roles=[])

no_change_password = re.compile(r"$|\*+")
@bp.route("/save_user.py", methods=("POST",))
@gets_parameters_from_request
@authentication.login_required
def save_user(request_login, firstname, lastname, email,
              newlogin=None, password1=None, password2=None,
              send_welcome_email=False):
    current_user = authentication.get_user()

    feedback = FormFeedback()

    # Let’s see if the login is still available
    if request_login == "__new":
        match = login_re.match(newlogin)
        if match is None:
            feedback.give("newlogin", "Ungültiger Benutzername")
        else:
            with cursor() as cc:
                count = model.users.User.count(
                    sql.where("login = ", sql.string_literal(newlogin)))

                #cc.execute("SELECT COUNT(*) FROM users WHERE login = %s",
                #           ( newlogin, ))

                if count > 0:
                    feedback.give(
                        "newlogin",
                        "Dieser Benutzername steht nicht zur Verfügung.")

    if no_change_password.match(password1) is None:
        if password1 != password2:
            feedback.give("password1", "Die Passwörter stimme nicht überein.")
        else:
            if not password_good_enough(password1):
                feedback.give("password1", password_strength_error_message)

        password = generate_password_hash(password1)
    else:
        password = None

    if request_login == "__new" and password is None:
        feedback.give("password1", "Bitte geben Sie ein Passwort ein.")

    feedback.validate_not_empty("firstname")
    feedback.validate_not_empty("lastname")
    feedback.validate_email("email")

    if feedback.is_valid():
        if request_login == "__new":
            login = newlogin
        else:
            login = request_login

        email = email.lower()

        with cursor() as cc:
            if request_login == "__new":
                cc.execute("INSERT INTO users (login, password, email) "
                           "     VALUES (%s, %s, %s)",
                           ( newlogin, password, email, ))

            data = {}
            for field in [ "firstname", "lastname", ]:
                data[field] = locals()[field]

            if password is not None:
                data["password"] = password

            command = sql.update("users",
                                 sql.where("login = ",
                                           sql.string_literal(login)),
                                 data)
            execute(command)

            commit()

            # ggF. Begrüßungs-eMail
            if send_welcome_email:
                site_url = get_site_url()
                reply_to = (f"{current_user.firstname} "
                            f"{current_user.lastname} "
                            f"<{current_user.email}>")

                if no_change_password.match(password1) is not None:
                    password = "<weißt Du schon>"
                else:
                    password = password1

                sendmail_template("admin/willkommens_email.txt",
                                  "Jugendkongress Wembaster",
                                  "webmaster@jugendkongress.org",
                                  f"{firstname} {lastname}",
                                  email,
                                  "Willkommen auf jugendkongress.org",
                                  locals(),
                                  headers={"Reply-To": reply_to},
                                  bcc=[current_user.email,])

            return redirect("/admin/users.py")
    else:
        return user_form(request_login=request_login, feedback=feedback)

def resolve_room_mates(bookings):
    # Create a dict matching (lower case) names and email-addresses
    # to bookings.
    d = {}
    for booking in bookings:
        d[booking.name.lower()] = booking
        d[booking.email] = booking

    # Now go through each of the names listed in the bookings
    # and see if we can find them.
    for booking in bookings:
        booking.resolve_room_mates(d)

@bp.route("/bookings.py", methods=('GET',))
@authentication.login_required
def bookings():
    congress = g.congresses.current

    details = (request.cookies.get("details", "false") == "true")

    bookings = model.congress.Booking.select(
        sql.where("year=%i" % congress.year),
        sql.orderby("lower(lastname), lower(firstname)"))

    resolve_room_mates(bookings)

    cursor = execute(f"SELECT food_preference, COUNT(*) AS count "
                     f"  FROM booking "
                     f" WHERE year = {congress.year} "
                     f" GROUP BY food_preference")

    food_preference_html = html.table()
    for id, count in cursor.fetchall():
        food_preference_html.append(html.tr(
            html.td(count, style="text-align: right"),
            html.td("✕"),
            html.td(model.congress.food_preference_html(id))))

    template = g.skin.load_template("skin/admin/bookings.pt")

    return template(congress=congress, bookings=bookings, details=details,
                    food_preference_html=food_preference_html)

@bp.route("/booking_name_form.py", methods=("GET", "POST",))
@authentication.login_required
@gets_parameters_from_request
def booking_name_form(id:int, firstname=None, lastname=None, email=None):
    template = g.skin.load_template("skin/admin/booking_name_form.pt")

    if request.method == "POST":
        feedback = FormFeedback()

        feedback.validate_not_empty("firstname")
        feedback.validate_not_empty("lastname")

        feedback.validate_not_empty("email")
        email_match = email_re.match(email)

        if email_match is None:
            feedback.give("email", "Keine gültige e-Mail Adresse.")

        if feedback.is_valid():
            execute(sql.update("booking", sql.where("id = %i" % id),
                               { "firstname": firstname,
                                 "lastname": lastname,
                                 "email": email }))
            commit()

            return redirect("/admin/bookings.py")
    else:
        feedback = NullFeedback()

    booking = model.congress.BookingForNameForm.select_by_primary_key(id)

    return template(feedback=feedback, booking=booking)
