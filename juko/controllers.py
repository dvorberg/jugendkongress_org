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
import re, dataclasses
import flask
from .utils import (gets_parameters_from_request, process_template,
                    rget, redirect)

from t4.res import email_re
from t4.passwords import random_password
from t4.sendmail import sendmail

from sqlclasses import sql

from .db import execute, query_one, insert_from_dict, commit
from .model.congress import (Booking, BookingForWorkshopAssignment,
                             Change, Congress, Room, resolve_room_mates,
                             Workshop)

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


class AssignableRoom(object):
    def __init__(self, no:str, section:str, beds:int, beds_overwrite:int|None):
        self.no = no
        self.section = section
        self._beds = beds
        self._beds_overwrite = beds_overwrite
        self.occupants = []

    @property
    def beds(self):
        if self._beds_overwrite:
            return self._beds_overwrite
        else:
            return self._beds

    def overwrite_beds(self, beds):
        self._beds_overwrite = beds

    @property
    def available(self):
        return self.beds - len(self.occupants)

    @property
    def gender(self):
        if len(self.occupants) == 0:
            return None
        else:
            return self.occupants[0].gender

    def permissable(self, occupant:Booking):
        gender = self.gender
        return (gender is None or occupant.gender == gender)


    def fits(self, occupant:Booking):
        return (occupant.max_beds >= self.beds and self.available)

    def append(self, occupant:Booking):
        if not self.permissable(occupant):
            raise ValueError("Not permissable")
        elif not self.available:
            raise ValueError("%s is full" % self.no)
        else:
            self.occupants.append(occupant)

    @property
    def NO(self):
        return self.no.upper()

def get_rooms_for(year):
    cursor = execute(f"SELECT room_no, section, beds, beds_overwrite "
                     f"  FROM booked_rooms "
                     f"  LEFT JOIN room ON room_no = no "
                     f"WHERE booked_rooms.year = {year} "
                     f"  AND room_no NOT IN "
                     f"( SELECT lower(room_overwrite) "
                     f"    FROM booking "
                     f"   WHERE year = {year} "
                     f"      AND room_overwrite IS NOT NULL)"
                     f"ORDER BY beds DESC")

    rooms = [ AssignableRoom(no, section, beds, o)
              for (no, section, beds, o) in cursor.fetchall() ]
    return dict([ (room.no, room,) for room in rooms ])

def get_room_data_for(year, include_overwritten=False):
    rooms_by_no = get_rooms_for(year)

    bookings = Booking.select(
        sql.where("year=%i " % year,
                  "AND room_overwrite IS NULL ",
                  "AND room_preference IS NOT NULL"),
        sql.orderby("room_preference"))
    resolve_room_mates(bookings)

    # If rooms are already set, transfer the info to the list.
    for booking in bookings:
        if booking.room:
            room = rooms_by_no[booking.room]
            room.append(booking)

    return rooms_by_no, bookings

def zimmer_zuordnung():
    rooms_by_no, bookings = get_room_data_for(flask.g.congress.year)
    unassignable = assign_rooms(rooms_by_no, bookings)
    return rooms_by_no.values(), unassignable

def find_groups_among(bookings):
    groups = []

    def find_friends(booking):
        group = set()

        def add(b):
            if b in group:
                return

            group.add(b)
            for a in b.found_room_mates:
                add(a)

            for a in bookings:
                if b in a.found_room_mates:
                    add(a)

        add(booking)

        return list(group)

    def ingroup(booking):
        for group in groups:
            if booking in group:
                return group
        return None

    for booking in bookings:
        if not ingroup(booking):
            group = find_friends(booking)
            if len(group) > 1:
                groups.append(group)

    return groups

def assign_rooms(rooms_by_no, bookings):
    year = flask.g.congress.year
    unassignable = []

    def place_into(booking, room):
        room.append(booking)
        booking.room = room.no

        execute("UPDATE booking SET room = %s WHERE id = %s",
                ( room.no, booking.id, ))

        bookings.remove(booking)

    def look_for_rooms():
        # Now go looking for rooms.
        while bookings:
            bookings.sort(key=lambda booking: (booking.room_preference,
                                               len(booking.found_room_mates),),
                          reverse=True)
            look_for_room(bookings[0])

    def look_for_room(booking):
        # Let’s see if any of the desired room mates already have a room
        # and it fits and so on…
        for rm in booking.found_room_mates:
            if rm.room is not None:
                room = rooms_by_no.get(rm.room, None)
                if room and room.fits(booking) and room.permissable(booking):
                    place_into(booking, room)
                    return

        # Go check by room size (that already have someone in them).
        for room in rooms_by_no.values():
            if room.available \
               and room.permissable(booking) \
               and room.fits(booking):
                place_into(booking, room)
                look_for_rooms()
                return

        # At this point we’ve run out of rooms.
        if booking.room_preference == '2-3 beds':
            for room in sorted(rooms_by_no.values(), key=lambda room:room.beds):
                if len(room.occupants) < 3 and room.permissable(booking):
                    room.overwrite_beds(3)
                    execute("UPDATE booked_rooms "
                            "   SET beds_overwrite = %s "
                            " WHERE room_no = %s AND year = %s",
                            (3, room.no, year,))
                    place_into(booking, room)
                    return

        #raise ValueError("No room for " + booking.name)
        unassignable.append(booking)
        bookings.remove(booking)

    groups = find_groups_among(bookings)

    def genders_match(group):
        gender = group[0].gender
        for booking in group[1:]:
            if booking.gender != gender:
                return False
        return True

    def find_room_for(group):
        for room in sorted(rooms_by_no.values(), key=lambda room:room.beds):
            if room.available >= len(group) \
               and ( room.gender == group[0].gender \
                     or room.gender is None ):
                return room

        return None

    # Place group in groups.
    for group in groups:
        if genders_match(group):
            room = find_room_for(group)
            if room is not None:
                for booking in group:
                    if booking.max_beds >= room.beds \
                       and booking.min_beds <= room.beds:
                        place_into(booking, room)

    look_for_rooms()

    return unassignable

def zimmer_zeigen(rooms):
    for room in rooms:
        if room.available != room.beds:
            print(room.no, f"({room.beds} Betten)")

            for booking in room.occupants:
                friends = []
                for name, rm in booking.resolved_room_mates:
                    if rm:
                        friends.append(rm.name)

                if friends:
                    friends = "(" + ",".join(friends) + ")"
                else:
                    friends = ""

                print("  ", booking.name, friends)
            print()

def groups_for_workshop(groups, workshop_id):
    for group in groups:
        group = [ booking
                  for booking in group
                  if workshop_id in booking.workshop_choices ]
        if len(group) > 1:
            yield group

@dataclasses.dataclass
class WorkshopInstance:
    workshop: Workshop
    phase: int
    bookings: list

    def available(self, booking_count):
        max = self.workshop.teilnehmer_max
        return (len(self.bookings) + booking_count <= max)

    def place(self, booking):
        self.bookings.append(booking)
        booking.placed.add(self.workshop.id)

def workshop_zuordnung():
    congress = flask.g.congresses.current
    year = congress.year

    instances = []
    workshop_by_id = {}
    for workshop in congress.workshops:
        workshop_by_id[workshop.id] = workshop
        for phase in workshop.phasen:
            instances.append(WorkshopInstance(workshop, phase, []))

    def instances_of(workshop):
        return sorted([ i for i in instances if i.workshop == workshop ],
                      key=lambda i: len(i.bookings))

    def place_group(workshop, group):
        for instance in instances_of(workshop):
            if instance.available(len(group)):
                for booking in group:
                    instance.place(booking)
                return

        # We can’t place the group as a whole and will place
        # single members later on.

    def place_booking(workshop, booking):
        for instance in instances_of(workshop):
            if instance.available(1):
                instance.place(booking)
                return

        ic("Can’t place", booking, workshop)

    bookings = Booking.select(sql.where("year=%i " % year,
                                        " AND ",
                                        "role = 'attendee'"))
    for booking in bookings:
        booking.placed = set()

    resolve_room_mates(bookings)
    groups = find_groups_among(bookings)

    for workshop in congress.workshops:
        for group in groups_for_workshop(groups, workshop.id):
            place_group(workshop, group)

    for booking in bookings:
        for workshop_id in booking.workshop_choices:
            if not workshop_id in booking.placed:
                workshop = workshop_by_id[workshop_id]
                place_booking(workshop, booking)

    # Store assignments in the db.
    values = []
    for instance in instances:
        for booking in instance.bookings:
            values.append( (booking.id,
                            instance.phase,
                            sql.string_literal(instance.workshop.id),) )

    execute(sql.insert("workshop_assignments",
                       ( "booking_id", "phase", "workshop_id",),
                       values))
