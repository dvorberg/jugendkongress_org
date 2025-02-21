WITH
first_checkins AS (
    SELECT room, MIN(checkin) AS first_show
      FROM booking
     WHERE year = 2025
     GROUP BY room
),
key_holder AS  (
    SELECT booking.room,
           id,
           firstname || ' ' || lastname AS name
      FROM first_checkins
      LEFT JOIN booking ON first_checkins.room = booking.room
                        AND first_show = booking.checkin
     WHERE year = 2025 AND checkin IS NOT NULL
)
SELECT * FROM key_holder

