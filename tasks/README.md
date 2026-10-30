# აპის ცხრილები

ამ ბაზაშია `devices`, `alert_settings`, `earthquakes`, `felt_reports`, `notification_outbox` და `notification_attempts`. მიწისძვრას უშვებს ies_monitoring. აქ ის ერთხელ ინახება, რევიზიების გარეშე.

გამოქვეყნებული მიწისძვრა უკვე აწყობილია [iesdata](https://iesdata.iliauni.edu.ge:3030/en/)-ზე. ინფორმაციას ვკითხულობთ საკუთარი endpoint-იდან:

`GET https://iesdata.iliauni.edu.ge:3030/api/publish_events/`

პასუხში `items[]`-ის თითო ელემენტს აქვს `id` (გამოქვეყნების ჩანაწერი) და `event` (თავად მიწისძვრა). აპი იყენებს `event.id`-ს. ეს რიცხვი იწერება `earthquakes.ies_event_id`-ში. `felt_reports` და შეტყობინებები უკავშირდება ლოკალურ `earthquakes.id`-ს.

მაგნიტუდა, დრო და კოორდინატები იმავე `event`-იდან მოდის. მაგნიტუდა ჯერ `ML`-ია, თუ არ არის — პირველი შევსებული მნიშვნელობა. სია ყველა გამოქვეყნებულ მიწისძვრას იძლევა. ვის ეგზავნება რომელიმე მათგანი, წყდება აქ, `alert_settings`-ის პოლიგონით და `min_magnitude`-ით ([06](06-recipients.md)).

## რიგი

1. [01 — PostGIS და ოთხი ცხრილი](01-schema.md)
2. [02 — devices](02-devices.md)
3. [03 — alert_settings](03-alert-settings.md)
4. [04 — felt_reports](04-felt-reports.md)
5. [05 — notification_outbox](05-notifications-sent.md)
6. [06 — ვის ეგზავნება](06-recipients.md)

