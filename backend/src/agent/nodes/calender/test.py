from calender_Client import get_calendar_service
service = get_calendar_service()

# Fetch next 5 upcoming events
events_result = service.events().list(
    calendarId='primary', maxResults=5, singleEvents=True, orderBy='startTime'
).execute()

events = events_result.get('items', [])
if not events:
    print("No upcoming events found.")
for event in events:
    print(event['summary'], event['start'].get('dateTime', event['start'].get('date')))
