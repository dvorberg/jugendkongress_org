##  Copyright 2024 by Diedrich Vorberg <diedrich@tux4web.de>
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
from .app_factory import skin
from .email import sendmail_template

from . import authentication, model
from .utils import (get_site_url, gets_parameters_from_request, redirect,
                    improve_typography, attr_dict, rget, rchecked,
                    OrderByHandler)
from .ptutils import js_string_literal


bp = Blueprint("authentication", __name__, url_prefix="/authentication")

@bp.route("/login.py", methods=('GET', 'POST'))
@gets_parameters_from_request
def login(login=None, password=None, redirect_to=None,
          description=None, alert_class=None):
    if rget("description") or rget("alert_class"):
        # The description will be put into the output HTML verbatimly
        # and must not come from the request.
        raise ValueError()

    template = skin.load_template("skin/authentication/login.pt")

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
                return redirect("/authentication/dashboard.py")
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
def logout():
    authentication.logout()
    return redirect(get_site_url(site_message="Sie wurden ausgeloggt."))

@bp.route("/forgott.py", methods=('GET', 'POST'))
@gets_parameters_from_request
def forgott(login=None):
    template = skin.load_template("skin/authentication/forgott.pt")

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
        cc.execute("DELETE FROM users.forgotten_password_requests "
                   "      WHERE user_login = %s"
                   "         OR ctime + '4 hours'::interval < NOW()",
                   (dbuser.login,) )

        # Create the new entry.
        slug = apple_style_random_password(4, 6)
        cc.execute("INSERT INTO users.forgotten_password_requests"
                   "            (user_login, slug)"
                   "     VALUES (%s, %s)",
                   (dbuser.login, slug,) )
        commit()

        # Send the email
        site_url = skin.site_url
        link = "%s/authentication/reset_password.py/%s" % ( site_url, slug, )

        login = dbuser.login
        firstname = dbuser.firstname
        lastname = dbuser.lastname

        sendmail_template( "forgotten_email.txt",
                           "Blütenlese Webmaster", "webmaster@blgd.tv",
                           "%s %s" % ( firstname, lastname, ), dbuser.email,
                           "Passwort-Anfrage auf blgd.tv", locals() )

password_strength_error_message = """\
Das Passwort ist nicht stark genug. Das Passwort muss enthalten:
Großbuchstaben, Kleinbuchstaben, eine Ziffer und ein
Sonderzeichen. Wenn eines von den vieren fehlt, meckert der Computer.
"""

@bp.route("/reset_password.py/<slug>", methods=("GET", "POST",))
@gets_parameters_from_request
def reset_password(slug, password1=None, password2=None):
    template = skin.load_template("skin/authentication/reset_password.pt")

    with cursor() as cc:
        # Remove stale links.
        cc.execute("DELETE FROM users.forgotten_password_requests "
                   "      WHERE ctime + '4 hours'::interval < NOW()")
        commit()

        cc.execute("SELECT user_login FROM users.forgotten_password_requests "
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
                cc.execute("UPDATE users.users SET password = %s "
                           " WHERE login = %s", ( password, user_login, ))
                commit()

            return redirect(get_site_url() + "/authentication/login.py")
    else:
        feedback = NullFeedback()

    return template(feedback=feedback, user_login=user_login)

@bp.route("/users.py", methods=("POST", "GET"))
@authentication.role_required("User Manager")
def users():
    template = skin.load_template("skin/authentication/users.pt")

    def delete_onclick(user):
        tmpl = ('return confirm("Möchten Sie den Eintrag von " + '
                '%s + " " + %s + " löschen?")')
        return tmpl % ( js_string_literal(user.firstname),
                        js_string_literal(user.lastname), )

    cursor = execute("SELECT name FROM users.user_roles "
                     " WHERE in_list ORDER BY name")
    user_roles = [ tpl[0] for tpl in cursor.fetchall() ]


    orderby = OrderByHandler(
        [ ("login", "Login",),
          ("lower(firstname), lower(lastname)", "Vorname",),
          ("lower(lastname), lower(firstname)", "Nachname",),
         ], "users_orderby")


    filter = attr_dict(session.get("users_filter", {}))
    if request.method == "POST":
        # Update the filter
        filter.filter_search = rget("filter_search")
        filter.role = rget("role", "")
        filter.active_only = rchecked("active_only")

        session["users_filter"] = filter

    where = None
    if filter.get("filter_search"):
        search_string = sql.string_literal("%" + filter.filter_search + "%")
        where = sql.where("firstname ILIKE ", search_string, " OR "
                          "lastname ILIKE ", search_string, " OR "
                          "login ILIKE ", search_string).and_(where)

    if filter.get("role"):
        where = sql.where("EXISTS (SELECT 1 FROM users.users_to_roles "
                          "         WHERE user_login = users.user_info.login "
                          "           AND role_name = ",
                          sql.string_literal(filter.role), ")").and_(where)

    if filter.get("active_only", True):
        where = sql.where("EXISTS (SELECT 1 FROM users.user_flags "
                          "         WHERE user_login = users.user_info.login "
                          "           AND flag = 'active')").and_(where)

    users = model.users.User.select(where, orderby.sql_clause())

    return template(users=users, user_roles=user_roles, orderby=orderby,
                    filter=filter, delete_onclick=delete_onclick)

@bp.route("/delete.py")
@authentication.role_required("User Manager")
@gets_parameters_from_request
def delete(login):
    if login == authentication.get_user().login:
        raise ValueError("Dude! You can’t delete yourself.")

    user = model.users.User.select_one(
        sql.where("login =", sql.string_literal(login)))

    # query_one("SELECT * FROM user_info WHERE login = %s" ,
    #                 (login,),
    #                 authentication.User)

    with cursor() as cc:
        cc.execute("DELETE FROM users.users WHERE login = %s", ( user.login, ))
        commit()

    return redirect("/authentication/users.py",
                    site_message="Der Eintrag von %s %s wurde gelöscht." % (
                        user.firstname, user.lastname,))

@bp.route("/delete_user_password.py")
@authentication.role_required("User Manager")
@gets_parameters_from_request
def delete_user_password(login):
    if login == authentication.get_user().login:
        raise ValueError("Dude! You can’t delete yourself.")

    user = model.users.User.select_one(
        sql.where("login =", sql.string_literal(login)))

    with cursor() as cc:
        cc.execute("UPDATE users.users SET password = NULL "
                   " WHERE login = %s", ( user.login, ))
        commit()

    return redirect("/authentication/users.py",
                    site_message="Das Passwort von %s %s wurde gelöscht." % (
                        user.firstname, user.lastname,))

@bp.route("/user_form.py", methods=("POST", "GET"))
@authentication.login_required
@gets_parameters_from_request
def user_form(request_login=None, feedback:FormFeedback=None):
    current_user = authentication.get_user()

    # Security precautions.
    if not current_user.is_root \
       and not current_user.has_role("User Manager") \
       or request_login is None:
        request_login = current_user.login

    if feedback is None:
        feedback = NullFeedback()

    if request_login == "__new":
        user = model.users.User.empty()
    else:
        user = model.users.User.select_one(
            sql.where("login = ",
                      sql.string_literal(request_login)))

    with cursor() as cc:
        cc.execute("SELECT name FROM users.user_roles ORDER BY name")
        roles = [ role for role, in cc.fetchall() ]

    template = skin.load_template("skin/authentication/user_form.pt")
    return template(dbuser=user,
                    feedback=feedback,
                    roles=roles)

@bp.route("/users/<user_name>.html")
@authentication.login_required
def profile_preview(user_name):
    template = skin.load_template("skin/authentication/profile_preview.pt")

    result = model.users.User.select(
        sql.where("firstname || ' ' || lastname = ",
                  sql.string_literal(user_name)))
    if len(result) < 1:
        return abort(404)
    else:
        user = result[0]
        return template(prediger=user, result=result)

@bp.route("/dashboard.py")
@authentication.login_required
@gets_parameters_from_request
def dashboard(request_login=None):
    template = skin.load_template("skin/authentication/dashboard.pt")

    if request_login is not None:
        assert authentication.get_user().has_role("User Manager"), Unauthorized

        dbuser = model.users.User.select_one(
            sql.where("login = ", sql.string_literal(request_login)))
    else:
        dbuser = model.users.User.current()

    today = datetime.date.today()
    todays_id = (   today.year  * 1000000
                  + today.month * 10000
                  + today.day   * 100
                  + 99 )

    def gd_query(future, foreign_key_column):
        where = sql.where(foreign_key_column, " = ",
                          sql.string_literal(dbuser.login),
                          " AND produce")

        if future:
            where = where.and_(sql.where("id > %i" % todays_id))
            limit = None
            dir = "ASC"
        else:
            where = where.and_(sql.where("id <= %i" % todays_id))
            limit = sql.limit(5)
            dir = "DESC"

        return model.gottesdienste.Gottesdienst_Alles.select(
            where, limit, sql.orderby("id " + dir))

    def vergangene_predigten():
        return gd_query(False, "prediger_login")
    def kommende_predigten():
        return gd_query(True, "prediger_login")
    def vergangene_videos():
        return gd_query(False, "editor_login")
    def kommende_videos():
        return gd_query(True, "editor_login")

    # def resource_cards_html_for(gottesdienst):
    #     prorium_where = sql.where(
    #         "proprium_ngb = %i" % gottesdienst.proprium_ngb)
    #     introitus = model.archive.Introitus.select(prorium_where)
    #     lesungen = model.archive.Lesung.select(
    #         prorium_where, sql.orderby("lesung_typ"))

    #     resources = introitus + lesungen

    #     view_macros = model.gottesdienste.gottesdienst_view_macros
    #     resource_card = view_macros.resource_card

    #     return [ resource_card(resource=resource)
    #              for resource in resources ]

    return template(dbuser=dbuser,
                    vergangene_predigten=vergangene_predigten,
                    kommende_predigten=kommende_predigten,
                    vergangene_videos=vergangene_videos,
                    kommende_videos=kommende_videos)
    # resource_cards_html_for=resource_cards_html_for

no_change_password = re.compile(r"$|\*+")

@bp.route("/save.py", methods=("POST",))
@gets_parameters_from_request
def save(request_login, firstname, lastname, email, phone,
         info, about, details, city,
         website, newlogin=None, password1=None, password2=None,
         skip_reminders_untill=None, roles:list=[],
         send_welcome_email:bool=False):
    current_user = authentication.get_user()

    # Security precautions.
    if not current_user.is_root and not current_user.has_role("User Manager"):
        request_login = current_user.login
        newlogin = None

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
    skip_reminders_untill = feedback.ensure_german_date(
        "skip_reminders_untill", required=False)
    if skip_reminders_untill and skip_reminders_untill < datetime.date.today():
        feedback.give("skip_reminders_untill",
                      "Dieses Datum darf nicht in der Vergangenheit liegen.")

    if feedback.is_valid():
        if request_login == "__new":
            login = newlogin
        else:
            login = request_login

        email = email.lower()

        with cursor() as cc:
            if request_login == "__new":
                cc.execute("INSERT INTO users.users (login, password, email) "
                           "     VALUES (%s, %s, %s)",
                           ( newlogin, password, email, ))

            data = {}
            for field in [ "email", "phone", "firstname", "lastname",
                           "website", "city", "skip_reminders_untill", ]:
                data[field] = locals()[field]

            for field in [ "info", "about", "details" ]:
                data[field] = improve_typography(locals()[field])

            if password is not None:
                data["password"] = password

            command = sql.update("users.users",
                                 sql.where("login = ",
                                           sql.string_literal(login)),
                                 data)
            execute(command)

            # The User Manager may change roles.
            if current_user.has_role("User Manager"):
                cc.execute("DELETE FROM users.users_to_roles "
                           " WHERE user_login = %s",
                           (login,))
                for role in roles:
                    cc.execute("INSERT INTO users.users_to_roles "
                               "     VALUES (%s, %s)",
                               ( login, role, ))

            user = model.users.User.from_dict({"login": login,
                                               "firstname": firstname,
                                               "lastname": lastname})
            model.users.store_profile_picture(user, "picture")

            for flag in ("active", "show-in-overview"):
                cc.execute("DELETE FROM users.user_flags "
                           " WHERE user_login = %s "
                           "   AND flag = %s", ( login, flag, ))
                if flag + "-flag" in request.form:
                    cc.execute("INSERT INTO users.user_flags VALUES (%s, %s)",
                               ( login, flag, ))

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

                sendmail_template("willkommens_email.txt",
                                  "Blütenlese Roboter", "webmaster@blgd.tv",
                                  f"{firstname} {lastname}",
                                  email,
                                  "Willkommen bei blgd.tv",
                                  locals(),
                                  headers={"Reply-To": reply_to},
                                  bcc=[current_user.email,])

            return redirect("/authentication/users/%s %s.html" % (
                firstname, lastname))
    else:
        return user_form(request_login=request_login, feedback=feedback)


@bp.route("/change_user_flag.py", methods=("GET",))
@gets_parameters_from_request
@authentication.role_required("User Manager")
def change_user_flag(user_login, flag, state):
    state = ( state == "true")

    # Checking the values of user_login and state is performed in-database:
    # The first is a foreign key to the users table, the latter a enum type.
    execute("DELETE FROM users.user_flags WHERE user_login = %s AND flag = %s",
            ( user_login, flag, ))
    if state is True:
        execute("INSERT INTO users.user_flags VALUES (%s, %s)",
                ( user_login, flag, ))

    commit()

    return make_response("Ok")
