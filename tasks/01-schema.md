# 01 — PostGIS და ცხრილები

## რას ვაკეთებთ

PostGIS და ეს ცხრილები: `devices`, `alert_settings`, `earthquakes`, `felt_reports`, `notification_outbox`, `notification_attempts`.

`regions` და რევიზიები არ იქმნება. მიწისძვრას უშვებს ies_monitoring. აქ ინახება ერთი ჩანაწერი: დრო, კოორდინატები, ადგილი, `is_automatic` და არჩეული მაგნიტუდა.

## როგორ

- გეომეტრია SRID 4326-ია: ზონა `MultiPolygon`, ანგარიშის წერტილი `Point`.
- `felt_reports.device_id` და `felt_reports.earthquake_id` არის `ON DELETE SET NULL`.
- `earthquakes.ies_event_id` არის iesdata-ს `event.id` და უნიკალურია. ლოკალური `earthquakes.id` სხვა ცხრილების გასაღებია.
- მაგნიტუდის ერთი წყვილი ინახება მიწისძვრაზე: ჯერ `ML`, თუ არ არის — პირველი მნიშვნელობა. მოთხოვნაში `magnitudes` მასივია.
- `created_by` და `updated_by` არის `user` ან `service` და სახელი. `updated_at` ივსება მაშინ, როცა განახლების ავტორიც მოდის.
- `notification_outbox` ერთ მიწისძვრასა და მოწყობილობას ერთ ტიპზე ერთხელ წერს. Expo-ს პასუხი `notification_attempts`-შია.
- `area_source` არის მხოლოდ `custom` ან `circle`.

## მზადაა, როცა

`earthquake_revisions` აღარ არის, და იგივე მიწისძვრა იმავე მოწყობილობას მეორედ აღარ ეწერება.
