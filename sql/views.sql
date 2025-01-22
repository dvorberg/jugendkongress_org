BEGIN;

set search_path = public;

DROP VIEW IF EXISTS booking_info CASCADE;
CREATE VIEW booking_info AS
   WITH wsc AS (
       SELECT booking_id, string_agg(workshop_id, ',') AS workshop_choices
         FROM workshop_choices
        GROUP BY booking_id
   ) 
   SELECT id, year, email, slug,
          firstname, lastname, 
          address, zip, city, phone, dob,
          gender, food_preference, food_remarks, lactose_intolerant,
          room, room_preference, room_mates, room_overwrite,
          ride_sharing_option, ride_sharing_start,
          musical_instrument,
          wsc.workshop_choices
     FROM booking
     LEFT JOIN wsc ON booking_id = booking.id;

-- GRANT SELECT ON booking_info TO jugendkongress; 

DROP VIEW IF EXISTS booking_short_list CASCADE;
CREATE VIEW booking_short_list AS
    SELECT id, year, email, slug,
           firstname, lastname, dob, city, phone, gender, room_overwrite,
           ctime, mtime
      FROM booking;
      
-- GRANT SELECT ON booking_for_name_form TO jugendkongress; 

DROP VIEW IF EXISTS booking_for_name_form CASCADE;
CREATE VIEW booking_for_name_form AS
    SELECT id, firstname, lastname, email FROM booking;

-- GRANT SELECT ON booking_for_name_form TO jugendkongress; 

DROP VIEW IF EXISTS room_info CASCADE;
CREATE VIEW room_info AS
    SELECT no, beds, section, year, (room_no IS NOT NULL) AS booked
      FROM room
      LEFT JOIN booked_rooms ON room_no = no;

-- GRANT SELECT ON room_info TO jugendkongress; 



COMMIT;
