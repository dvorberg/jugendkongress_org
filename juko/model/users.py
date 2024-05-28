import string, datetime, os.path as op

from PIL import Image, ImageFilter, ImageDraw, ImageFont

from ll.xist import xsc
from ll.xist.ns import html

from t4 import sql
from t4.typography import pretty_german_date

from flask import request, session

from ..db import dbobject, Result, execute
from ..upload_manager import UploadManager, make_image_versions
from ..skinning import get_site_url
from ..utils import rget

from ..app_factory import skin

class UserResult(Result):
    def card_view(self, **kw):
        return prediger_view_macros.card_view(result=self, **kw)

class has_login:
    pass

class _BaseUser(dbobject, has_login):
    """
    User class that’s queried for every request that contains minimal
    data on the current user.
    """
    __schema__ = "users"
    __relation__ = "users"
    __primary_key_column__ = "login"

    @classmethod
    def current(cls):
        """
        Return the current user object as an object of this class.
        """
        from .. import authentication
        return cls.select_by_primary_key(session.get("user_login"))

    @property
    def roles(self):
        return self._roles

    @roles.setter
    def roles(self, roles):
        # The “,” is set as dilimiter in views.sql.
        if roles is None:
            self._roles = []
        else:
            if type(roles) == set:
                self._roles = roles
            else:
                self._roles = set(roles.split(","))

    def has_role(self, *args):
        for roles in args:
            if type(roles) == str and roles in self.roles:
                return True
            else:
                for role in roles:
                    if role in self.roles:
                        return True
        return False

    @property
    def is_root(self):
        return self.has_role("Root")

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return (not self.is_anonymous)

    @property
    def is_manager(self):
        return self.has_role("Manager")


class LoginUser(_BaseUser):
    __view__ = "login_info"

    @property
    def full_user(self):
        if not hasattr(self, "_full_user"):
            self._full_user = User.select_by_primary_key(self.login)

        return self._full_user

    @property
    def firstname(self):
        return self.full_user.firstname

    @property
    def lastname(self):
        return self.full_user.lastname

    @property
    def email(self):
        return self.full_user.email

    @property
    def phone(self):
        return self.full_user.phone

class User(_BaseUser):
    __view__ = "user_info"
    __result_class__ = UserResult

    @property
    def name(self):
        if hasattr(self, "_name"):
            return self._name
        else:
            return f"{self.firstname} {self.lastname}"

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def shortname(self):
        if self.firstname:
            return "%s. %s" % ( self.firstname[0], self.lastname, )
        else:
            return self.lastname

class AnonymousUser:
    roles = set()
    is_root = False
    is_anonymous = True
    is_authenticated = False

    is_manager = False

    login = None
    email = None

    def has_role(self, *roles):
        return False

user_ids_by_login = {}
def user_id_by_login(login):
    if not login in user_ids_by_login:
        tpl = query_one("SELECT id FROM users.users "
                        " WHERE login = %s", ( login, ))
        if tpl is None:
            raise KeyError(login)
        else:
            user_ids_by_login[login] = tpl[0]

    return user_ids_by_login[login]
