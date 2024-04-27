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

import functools

from flask import g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized, Forbidden

from ll.xist import xsc
from ll.xist.ns import html

from .db import dbobject, Result, select_one
from .model import users as model

def get_user():
    user_login = session.get("user_login")

    if user_login is None:
        return model.AnonymousUser()
    else:
        if "user" not in g:
            g.user = select_one( ("SELECT id, roles, shortname "
                                  "  FROM users.login_info "
                                  " WHERE login = %s"),
                                 ( user_login, ),
                                 model.LoginUser )
            g.user.login = user_login

        return g.user


def login(login, password):
    authdata = select_one("SELECT login, password FROM users.users "
                          " WHERE login = %s"
                          "    OR lower(email) = lower(%s)",
                          ( login, login, ))
    if password \
       and authdata \
       and check_password_hash(authdata.password, password):
        session["user_login"] = authdata.login
    else:
        raise Unauthorized("Login failed.")

def logout():
    if "user" in g:
        g.pop("user")

    session["user_login"] = None

def login_required(func):
    @functools.wraps(func)
    def wrapped_func(*args, **kwargs):
        if get_user().is_anonymous:
            raise Unauthorized()
        return func(*args, **kwargs)

    return wrapped_func

class role_required:
    def __init__(self, *roles):
        self.roles = roles

    def __call__(self, func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            if not get_user().is_root and \
               not get_user().has_role(self.roles):
                raise Forbidden()
            return func(*args, **kwargs)

        return wrapped_func
