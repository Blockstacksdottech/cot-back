Fix Seasonality Update in Premium Calendar
The user reported that seasonality data is not updating in the Premium Calendar (
pages/panel/calendar.js
) but works correctly in the Historical Admin Calendar (
pages/panel/admcalendar.js
).

My investigation shows:

calendar.js
 fetches data from user-seasonality (no parameters).
admcalendar.js
 fetches data from adm-date-seasonality?date=YYYY-MM-DD.
The user-seasonality endpoint appears to be returning stale data. The adm-date-seasonality endpoint works correctly.

User Review Required
WARNING

I am switching the endpoint from user-seasonality to adm-date-seasonality. There is a risk that adm-date-seasonality requires admin permissions. If regular users cannot access this endpoint, they will see an empty calendar or no seasonality data. Please verify if adm-date-seasonality is accessible to premium users.

Proposed Changes
Panel
[MODIFY] 
calendar.js
Import 
formatDateYYYY
 from ../../helpers.
In 
fetchData
, generate the current date using 
formatDateYYYY(new Date())
.
Update the API call to use adm-date-seasonality?date=${currentDate}.


this is what the initial analysis gave but can you verify that my eendpoiints if they were working perfectly and suggst a. better fix
