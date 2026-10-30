# 06 — ვის ეგზავნება რომელ მიწისძვრაზე

## რას ვაკეთებთ

`GET /api/publish_events/` მხოლოდ გამოქვეყნებულ მიწისძვრებს აბრუნებს. ის არ ამბობს, რომელ მოწყობილობას ეგზავნება. ერთი მიწისძვრა ბევრ მოწყობილობას შეიძლება მოხვდეს, და ერთ მოწყობილობას დროთა განმავლობაში ბევრი მიწისძვრა, თითო მხოლოდ ერთხელ.

ყოველ მიწისძვრაზე ვარჩევთ იმ მოწყობილობებს, რომელთა ზონაშიც ეპიცენტრი ხვდება და რომელთა ზღვარსაც მაგნიტუდა სცდება.

## როგორ

წყარო არის `items[].event`: `id`, `latitude`, `longitude`, `magnitudes`. `items[].id` არ გამოიყენება.

მაგნიტუდა: ჯერ `ML`, თუ არ არის — პირველი შევსებული მნიშვნელობა.

მოწყობილობა შედის სიაში, თუ ოთხივე ერთად სრულდება:

1. `alert_settings` აქვს და `enabled` ჭეშმარიტია. ჩანაწერის გარეშე შეტყობინება არ ეგზავნება.
2. არჩეული მაგნიტუდა `min_magnitude`-ზე ნაკლები არ არის.
3. ეპიცენტრი ხვდება `area`-ში. `custom` და `circle` ერთნაირად მოწმდება, ორივე უკვე `MultiPolygon`-ია.
4. მოწყობილობა აქტიურია, `push_token` შევსებულია, და ეს მიწისძვრა ამ მოწყობილობაზე ჯერ არ დევს `notification_outbox`-ში.

არჩევა PostGIS-ში ხდება, აპის კოდში პოლიგონების ჩამოთვლით არა. გრძედი პირველია, განედი მეორე:

```sql
SELECT d.device_id, d.push_token, d.language
FROM alert_settings AS a
JOIN devices AS d ON d.device_id = a.device_id
WHERE a.enabled
  AND a.min_magnitude <= :magnitude
  AND d.push_token IS NOT NULL
  AND ST_Intersects(
        a.area,
        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
      )
  AND d.is_active
  AND NOT EXISTS (
        SELECT 1
        FROM notification_outbox AS n
        WHERE n.earthquake_id = :earthquake_id
          AND n.device_id = d.device_id
      );
```

`alert_settings_area_idx` ამ გადაკვეთას აჩქარებს. დაბრუნებული მოწყობილობები იწერება `notification_outbox`-ში ([05](05-notifications-sent.md)). Expo მხოლოდ ახალ სტრიქონზე იძახება, და პასუხი `notification_attempts`-ში რჩება.

## მზადაა, როცა

ერთი და იგივე მიწისძვრა მოწყობილობას აწვდის მხოლოდ მაშინ, როცა ეპიცენტრი მის პოლიგონშია და მაგნიტუდა მის ზღვარს აკმაყოფილებს. პოლიგონის გარეთ, გამორთულ ზონაზე, ტოკენის გარეშე და უკვე გაგზავნილ წყვილზე შეტყობინება არ მიდის.
