BEGIN;

set search_path = public;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE OR REPLACE FUNCTION public.update_mtime() RETURNS trigger AS'
BEGIN
  /* Funktion liefert aktuellen Timestamp fuer Feld modification_time */
  NEW.mtime := now();
  RETURN NEW;
END;
' LANGUAGE 'plpgsql'; 


CREATE TYPE gender AS ENUM ('male', 'female', 'nn' );
CREATE TYPE food_preference AS ENUM ('meat', 'vegetarian', 'vegan');
CREATE TYPE room_preference AS ENUM  ('4-8 beds', '2-3 beds');
CREATE TYPE ride_sharing_option AS ENUM  ('offer', 'seek', 'none');
CREATE TYPE role AS ENUM ('team', 'speaker', 'attendee');
CREATE TYPE mode_of_travel AS ENUM  ('none', 'car', 'rail');


CREATE TABLE booking
(
    id SERIAL PRIMARY KEY,

    year INTEGER,
    email citext NOT NULL,
    slug CHAR(9) NOT NULL,

    UNIQUE(year, email),
    UNIQUE(slug),

    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    zip TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',    
    phone TEXT NOT NULL DEFAULT '',
    dob DATE,
    gender gender,
    food_preference food_preference,
    food_remarks TEXT NOT NULL DEFAULT '',
    lactose_intolerant BOOLEAN NOT NULL DEFAULT false,
    
    room_preference room_preference, 
    room_mates TEXT NOT NULL DEFAULT '',

    ride_sharing_option ride_sharing_option NOT NULL DEFAULT 'none',
    ride_sharing_start TEXT,

    musical_instrument TEXT NOT NULL DEFAULT '',

    room_overwrite VARCHAR(4), 
    keep_data BOOLEAN NOT NULL DEFAULT false,

    role role NOT NULL DEFAULT 'attendee',

    ctime TIMESTAMP NOT NULL DEFAULT NOW(),
    mtime TIMESTAMP NOT NULL DEFAULT NOW(),

    user_agent TEXT
);

CREATE TRIGGER "update_mtime_on_booking" 
   BEFORE UPDATE ON booking
   FOR EACH ROW EXECUTE PROCEDURE public.update_mtime();

CREATE TABLE workshop_choices
(
    booking_id INTEGER REFERENCES booking ON DELETE CASCADE,
    workshop_id TEXT NOT NULL,

    UNIQUE (booking_id, workshop_id)
);

CREATE TABLE workshop_phases
(
    year INTEGER NOT NULL,
    number INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',

    PRIMARY KEY (year, number)
);

CREATE TABLE workshop_assignments
(
    booking_id INTEGER REFERENCES booking ON DELETE CASCADE,
    phase SMALLINT NOT NULL,
    workshop_id TEXT NOT NULL,

    UNIQUE (booking_id, phase, workshop_id)
);

CREATE TABLE remarks
(
    booking_id INTEGER REFERENCES booking ON DELETE CASCADE,

    author TEXT NOT NULL,
    remark TEXT NOT NULL,

    ctime TIMESTAMP NOT NULL DEFAULT NOW()
);


CREATE TABLE users (
       id SERIAL,
       login TEXT NOT NULL PRIMARY KEY,
       password TEXT,
       firstname TEXT NOT NULL DEFAULT '',
       lastname TEXT NOT NULL DEFAULT '',
       email TEXT NOT NULL UNIQUE
);

INSERT INTO users (login, firstname, lastname, email) VALUES
    ( 'diedrich', 'Diedrich', 'Vorberg', 'diedrich@tux4web.de' );


CREATE TABLE forgotten_password_requests (
       user_login TEXT NOT NULL UNIQUE REFERENCES users ON DELETE CASCADE,
       ctime TIMESTAMP NOT NULL DEFAULT NOW(),
       slug TEXT NOT NULL UNIQUE
);


CREATE TABLE room
(
    no TEXT PRIMARY KEY,
    beds INTEGER NOT NULL
);

CREATE TABLE booked_rooms
(
    year INTEGER NOT NULL,
    room_no TEXT NOT NULL REFERENCES room
);

COMMIT;

