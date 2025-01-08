BEGIN;

set search_path = public;

DROP VIEW IF EXISTS booking_info CASCADE;
CREATE VIEW booking_info AS
   WITH wsc AS (
       SELECT booking_id, string_agg(workshop_id, ',') AS workshop_choices
         FROM workshop_choices
        GROUP BY booking_id
   ) 
   SELECT year, email, slug,
          firstname, lastname, 
          address, zip, city, phone, dob,
          gender, food_preference, food_remarks, lactose_intolerant,
          room_preference, room_mates,
          ride_sharing_option, ride_sharing_start,
          musical_instrument,
          wsc.workshop_choices
     FROM booking
     LEFT JOIN wsc ON booking_id = booking.id;

-- GRANT SELECT ON booking_info TO jugendkongress; 

DROP VIEW IF EXISTS booking_short_list CASCADE;
CREATE VIEW booking_short_list AS
    SELECT year, email, slug,
           firstname, lastname, dob, city, phone, gender, room_overwrite,
           ctime, mtime
      FROM booking
      
-- GRANT SELECT ON booking_short_list TO jugendkongress; 

COMMIT;
