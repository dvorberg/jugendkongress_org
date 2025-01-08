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

class User(dbobject):
    """
    User class that’s queried for every request that contains minimal
    data on the current user.
    """
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
        return { "Authenticated", "Manager", }

    @roles.setter
    def roles(self, roles):
        raise AttributeError("Roles cannot be set.")

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
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return (not self.is_anonymous)

    @property
    def is_manager(self):
        return self.has_role("Manager")

# On blgd.tv these used to be separate because the users table had wide
# columns.
LoginUser = User

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
        tpl = query_one("SELECT id FROM users "
                        " WHERE login = %s", ( login, ))
        if tpl is None:
            raise KeyError(login)
        else:
            user_ids_by_login[login] = tpl[0]

    return user_ids_by_login[login]
