# API reference

ყველა endpoint-ის საერთო prefix არის `/api/v1`. Swagger ხელმისაწვდომია `/docs/`-ზე.
JSON request-ებს უნდა ჰქონდეს `Content-Type: application/json`.

API-ში authentication/authorization middleware ამჟამად არ არის ჩართული.

## 1. Devices

### `GET /devices/`

აბრუნებს მოწყობილობების სიას.

Query:

- `limit` — 1–200, default `100`.

Response: `{ "items": [...], "total": 1, "limit": 100 }`.
Device response-ში FCM token არ ბრუნდება; token ცალკე resource-ია.

### `POST /devices/`

არეგისტრირებს ახალ device-ს ან აახლებს არსებულ device metadata-ს იმავე `device_id`-ზე.

```json
{
  "device_id": "11111111-1111-4111-8111-111111111111",
  "platform": "android",
  "language": "ka",
  "app_version": "1.2.0"
}
```

`platform`: `ios`, `android`, `web`. `language`: `ka`, `en`.
ახალი ჩანაწერი აბრუნებს `201`-ს, არსებული — `200`-ს.

### `GET /devices/{device_id}`

აბრუნებს ერთ device-ს. უცნობი ან არასწორი UUID აბრუნებს `404`/`400`-ს.

## 2. FCM tokens

### `GET /devices/{device_id}/fcm-tokens/`

აბრუნებს device-ის FCM token-ს სიაში. პროექტის წესით სია შეიძლება შეიცავდეს მაქსიმუმ ერთ აქტიურ ჩანაწერს.

### `POST /devices/{device_id}/fcm-tokens/`

არეგისტრირებს ან ცვლის device-ის აქტიურ token-ს.

```json
{
  "fcm_token": "firebase-registration-token"
}
```

ახალი token-ის ჩაწერისას ძველი token იშლება. იგივე token-ის სხვა device-ზე რეგისტრაცია მას ახალ device-ზე გადააბამს.

Responses: `201` ახალი token, `200` არსებული token-ის განახლება, `400` validation error, `404` device not found, `409` conflict.

### `DELETE /devices/{device_id}/fcm-tokens/{token_id}`

თიშავს შეტყობინებების მიღებას და შლის token-ს. აბრუნებს `204`-ს.
ხელახლა ჩართვისას აპმა POST-ით უნდა დაარეგისტრიროს მიმდინარე FCM token.

## 3. Location

ყველა location endpoint მუშაობს უკვე რეგისტრირებულ device-ზე:
`/devices/{device_id}/location/`.

### `GET /devices/{device_id}/location/`

აბრუნებს sharing state-ს და ბოლო მდებარეობას. ჯერ არ მიღებული კოორდინატები `null`-ია.

### `PATCH /devices/{device_id}/location/`

ცვლის მხოლოდ sharing state-ს:

```json
{ "location_sharing_enabled": true }
```

გამორთვისას ბოლო მდებარეობა არ იშლება.

### `PUT /devices/{device_id}/location/`

ინახავს ან ანაცვლებს ბოლო location fix-ს:

```json
{
  "latitude": 41.7151,
  "longitude": 44.8271,
  "accuracy": 10,
  "recorded_at": "2026-11-04T12:30:00Z"
}
```

`latitude` არის `-90..90`, `longitude` `-180..180`; `accuracy` არ შეიძლება იყოს უარყოფითი.
`recorded_at` optional-ია, მაგრამ თუ იგზავნება, timezone უნდა ჰქონდეს. Sharing-ის გამორთვისას ჩაწერა აბრუნებს `403`-ს.

## 4. Alert settings

### `GET /alert-settings/`

აბრუნებს ყველა alert area-ს. Query: `limit` 1–200, default `100`.

### `GET /devices/{device_id}/alert-settings`

აბრუნებს ერთი device-ის alert settings-ს.

### `PUT /devices/{device_id}/alert-settings`

ქმნის ან მთლიანად ანაცვლებს device-ის ერთ alert area-ს.

Custom polygon:

```json
{
  "enabled": true,
  "min_magnitude": 3.0,
  "area_source": "custom",
  "area": { "type": "Polygon", "coordinates": [] }
}
```

Circle:

```json
{
  "enabled": true,
  "min_magnitude": 3.0,
  "area_source": "circle",
  "latitude": 41.7151,
  "longitude": 44.8271,
  "radius_m": 120000
}
```

`area_source` არის `custom` ან `circle`; `min_magnitude` — `0..10`; radius — `0..2000000` მეტრი.

## 5. Felt reports

### `GET /felt-reports/`

აბრუნებს felt reports-ს `created_at`-ის კლებადობით. Query: `limit` 1–200.

### `POST /devices/{device_id}/felt-report/`

ინახავს კონკრეტული, წინასწარ რეგისტრირებული device-ის felt report-ს.
`device_id` URL-დან მოდის და request body-ში არ იგზავნება.

აუცილებელი ველებია: `intensity` (`MILD`, `MODERATE`, `SEVERE`),
`time_ago`, `latitude` და `longitude`.
`accuracy` optional-ია და არ შეიძლება უარყოფითი იყოს.
`created_at` response-ში ბრუნდება და სერვერი ავტომატურად ავსებს report-ის
მიღების მომენტში.

```json
{
  "intensity": "MODERATE",
  "time_ago": 5,
  "latitude": 41.7151,
  "longitude": 44.8271,
  "accuracy": 10
}
```

`latitude` უნდა იყოს `-90..90`-ში, `longitude` — `-180..180`-ში.
კოორდინატები ინახება მხოლოდ `latitude`, `longitude` და `accuracy` ველებში;
report მიწისძვრას არ უკავშირდება.

### `GET /devices/{device_id}/felt-report/`

აბრუნებს ამ device-ის მიერ გამოგზავნილ report-ებს და მათ საერთო რაოდენობას.
Query: `limit` 1–200, default `100`. სია დალაგებულია `created_at`-ის
კლებადობით.

პასუხის ფორმატი:

```json
{
  "device_id": "11111111-1111-4111-8111-111111111111",
  "items": [],
  "total": 0,
  "limit": 100
}
```

### `GET /felt-reports/{report_id}`

აბრუნებს ერთ felt report-ს.

## 6. Earthquakes

### `GET /earthquakes/`

აბრუნებს შენახულ მიწისძვრებს. Query: `limit` 1–200.

### `POST /earthquakes/`

ინახავს validated earthquake-ს. საჭიროა `event_id`, `iesdata_id`, `seiscomp_oid`, `is_automatic`, `origin` და მინიმუმ ერთი magnitude.

### `GET /earthquakes/{event_id}`

აბრუნებს `ies_event_id`-ით მოძებნილ მიწისძვრას.

### `PUT /earthquakes/{event_id}`

არსებულ მიწისძვრას სრულად ანაცვლებს. URL-ის `event_id` და payload-ის `event_id` ერთმანეთს უნდა ემთხვეოდეს.

### `DELETE /earthquakes/{event_id}`

შლის მიწისძვრას და cascade-ით მის notification outbox/attempt ჩანაწერებს. აბრუნებს `204`-ს.

## 7. Notifications

### `GET /notifications/stats`

აბრუნებს საერთო რაოდენობას, device/event count-ს და სტატუსების დაყოფას.

### `GET /notifications/`

აბრუნებს notification outbox-ს. Query: `limit`, `event_id`, `device_id`, `status`.
`status`: `pending`, `processing`, `ok`, `error`.

### `POST /notifications/`

```json
{ "event_id": 16 }
```

არჩევს მოწყობილობებს, რომლებსაც აქვთ აქტიური device, enabled alert settings, ჩართული FCM token და შესაბამისი გეოგრაფიული/magnitude პირობა. ერთ earthquake-device-notification type კომბინაციას მეორედ არ წერს.

### `GET /notifications/{outbox_id}/attempts`

აბრუნებს კონკრეტული outbox row-ის attempts-ს. Query: `limit` 1–200.

## საერთო შეცდომები

Validation error-ის ტიპური ფორმაა:

```json
{
  "error": "validation_error",
  "message": "..."
}
```

Resource not found აბრუნებს `404`-ს, conflict — `409`-ს, ხოლო database/server failure — `500`-ს.
