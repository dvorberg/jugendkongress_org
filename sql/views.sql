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

COMMIT;
