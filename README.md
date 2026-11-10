# IES_APP_Backend

Flask API for the IES earthquake mobile application. The layout matches Ies_Monitoring: `run.py`, `app/extensions.py`, `app/models`, Flask-RESTX namespaces, and Flask-Migrate.

The database password stays in `.env`. The app role is not the `postgres` superuser.

```bash
bash scripts/bootstrap_db.sh
venv/bin/flask --app run init_db --confirm-text RESET_DB
venv/bin/flask --app run populate_db
venv/bin/python run.py
```

`bootstrap_db.sh` sudo-ს პაროლს გთხოვს, `.env`-ის როლსა და ბაზას ქმნის და PostGIS-ს აყენებს.

`init_db` ცხრილებს თავიდან ქმნის და `--confirm-text RESET_DB` სჭირდება. Production-ში დამატებით `--force` უნდა გადასცე. `populate_db` ქმნის ერთ სატესტო მოწყობილობას, მის FCM token-ს, თბილისის 120 კმ alert area-ს, ერთ შენახულ მიწისძვრას, ერთ felt ანგარიშს და ერთ შეტყობინებას `notification_outbox`-ში. `event_id` უახლოესი გამოქვეყნებული მიწისძვრის `event.id`-ია და `earthquakes.ies_event_id`-ში ინახება. ხელახლა გაშვება იმავე ჩანაწერს არ იმეორებს.

Swagger: `http://127.0.0.1:5000/docs/`

დეტალური დოკუმენტაცია იხილე [docs/](docs/README.md)-ში.

| Method | Path | Stores |
| --- | --- | --- |
| GET | `/api/v1/devices/` | stored devices (`?limit=`) |
| GET | `/api/v1/devices/<id>` | one device |
| POST | `/api/v1/devices/` | register or update device metadata |
| GET, POST | `/api/v1/devices/<device_id>/fcm-tokens/` | read or register the device's single active FCM token |
| DELETE | `/api/v1/devices/<device_id>/fcm-tokens/<token_id>` | disable notifications and remove the FCM token |
| GET | `/api/v1/devices/<device_id>/location/` | sharing state and last known location |
| PATCH | `/api/v1/devices/<device_id>/location/` | enable or disable location sharing |
| PUT | `/api/v1/devices/<device_id>/location/` | replace an existing device's latest location |
| GET | `/api/v1/alert-settings/` | stored alert areas (`?limit=`) |
| GET | `/api/v1/devices/<id>/alert-settings` | one device's polygon |
| PUT | `/api/v1/devices/<id>/alert-settings` | one polygon and minimum magnitude |
| GET | `/api/v1/felt-reports/` | stored felt reports (`?limit=`) |
| GET | `/api/v1/felt-reports/<id>` | one felt report |
| POST | `/api/v1/devices/<device_id>/felt-report/` | submit a felt report for a device |
| GET | `/api/v1/devices/<device_id>/felt-report/` | list reports submitted by a device (`?limit=`) |
| GET, POST | `/api/v1/earthquakes/` | list earthquakes, or store a new one |
| GET, PUT, DELETE | `/api/v1/earthquakes/<event_id>` | one earthquake; PUT replaces it, DELETE removes it |
| GET | `/api/v1/notifications/stats` | totals, status counts, and counts per earthquake |
| GET | `/api/v1/notifications/` | outbox rows (`?limit=`, `event_id`, `device_id`, `status`) |
| GET | `/api/v1/notifications/<id>/attempts` | Expo attempts for one outbox row |
| POST | `/api/v1/notifications/` | `event_id` of a stored earthquake; queues recipients |

### Location settings

Register the device with `POST /api/v1/devices/` first. Location endpoints only
operate on an existing device; they never register one. Location sharing starts
disabled. Enable it with `PATCH /api/v1/devices/<device_id>/location/` and
`{"location_sharing_enabled": true}` before submitting a location.

Send location fixes with `PUT` to
`/api/v1/devices/<device_id>/location/`. It replaces the device's single latest
location in `location_settings`.

```json
{
  "latitude": 41.7151,
  "longitude": 44.8271,
  "accuracy": 10,
  "recorded_at": "2026-11-04T12:30:00Z"
}
```

`latitude` and `longitude` are required and must be in `-90..90` and `-180..180`.
`accuracy` is optional, measured in meters, and cannot be negative. `recorded_at`
is the location-fix timestamp and must include a timezone; if omitted, it
defaults to the server's current UTC time. The response's `location_updated_at`
is the server UTC time when the fix was saved.

`GET /api/v1/devices/<device_id>/location/` returns the sharing state and latest fix.
Location fields are `null` until the first fix arrives. Disabling sharing with
`PATCH` preserves the saved location and blocks new submissions with `403`.
There is no location deletion endpoint.

### Devices and FCM tokens

`POST /api/v1/devices/` registers the device and updates only its device
metadata (`device_id`, `platform`, `language`, and `app_version`). FCM tokens
are managed separately.

Register or replace the active token after the user enables notifications:

```http
POST /api/v1/devices/{device_id}/fcm-tokens/
Content-Type: application/json
```

```json
{
  "fcm_token": "firebase-registration-token"
}
```

Each device can have only one active token. Registering a new token deletes the
previous token for that device. The same token cannot belong to two devices;
registering it for another device moves it to the new device.

Read the active token:

```http
GET /api/v1/devices/{device_id}/fcm-tokens/
```

Disable notifications by deleting the token:

```http
DELETE /api/v1/devices/{device_id}/fcm-tokens/{token_id}
```

There is no PATCH endpoint for FCM tokens. To enable notifications again, the
client registers the current token with POST.

### Alert settings

`PUT /api/v1/devices/{device_id}/alert-settings` creates or replaces the
device's single alert area. Use `area_source: "circle"` with `latitude`,
`longitude`, and `radius_m`, or `area_source: "custom"` with a Polygon or
MultiPolygon GeoJSON object in `area`. `min_magnitude` must be between `0`
and `10`; `enabled` defaults to `true`.

### Felt reports

`POST /api/v1/devices/{device_id}/felt-report/` accepts `intensity`,
non-negative `time_ago`, `latitude`, `longitude`, and optional non-negative
`accuracy`. The `device_id` is taken from the URL and
must belong to a registered device.

```json
{
  "intensity": "MODERATE",
  "time_ago": 5,
  "latitude": 41.7151,
  "longitude": 44.8271,
  "accuracy": 10
}
```

### Earthquakes

`POST /api/v1/earthquakes/` stores a validated earthquake. `PUT
/api/v1/earthquakes/{event_id}` replaces an existing event, and `DELETE`
removes it together with queued notifications. Earthquake coordinates must be
within valid latitude/longitude ranges, depth cannot be negative, and at least
one magnitude is required.

### Notifications

`POST /api/v1/notifications/` accepts a stored earthquake `event_id` and
creates pending outbox rows for active devices that have enabled alert settings,
an active FCM token, and a matching alert area/magnitude. Duplicate
earthquake-device recipients are ignored.

Notification list and attempt endpoints support `limit` (1–200). The list also
supports `event_id`, `device_id`, and `status` filters. Stats are available at
`GET /api/v1/notifications/stats`.
