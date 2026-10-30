# 05 — notification_outbox

## რას ვაკეთებთ

მიწისძვრაზე შერჩეულ მოწყობილობას ვწერთ `notification_outbox`-ში. Expo-ს ყოველი ცდა `notification_attempts`-შია: `expo_ticket_id`, `expo_receipt_id`, სტატუსი და შეცდომა.

## როგორ

ერთი მიწისძვრა, ერთი მოწყობილობა და ერთი `notification_type` მეორედ აღარ იწერება.

ახალი სტრიქონის სტატუსია `pending`, `attempt_count` ნულია. გაგზავნისას იზრდება `attempt_count` და ემატება `notification_attempts`. წარმატებაზე outbox ხდება `ok` და ივსება `processed_at`. შეცდომაზე რჩება `error`.

`locked_at` ნიშნავს, რომ სტრიქონს ამჟამად ამუშავებს გამგზავნი (`processing`).

## მზადაა, როცა

იგივე მიწისძვრა იმავე მოწყობილობას მეორედ აღარ ემატება, და ყოველი Expo-ს ცდა ცალკე ჩანაწერია.
