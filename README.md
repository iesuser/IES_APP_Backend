# IES_APP_Backend

Flask API for the IES earthquake mobile application. The layout matches Ies_Monitoring: `run.py`, `app/extensions.py`, `app/models`, Flask-RESTX namespaces, and Flask-Migrate.

The database password stays in `.env`. The app role is not the `postgres` superuser.

```bash
bash scripts/bootstrap_db.sh
venv/bin/flask --app run init_db --confirm-text RESET_DB
venv/bin/flask --app run upgrade_db
venv/bin/flask --app run populate_db
venv/bin/python run.py
```

`bootstrap_db.sh` sudo-ს პაროლს გთხოვს, `.env`-ის როლსა და ბაზას ქმნის და PostGIS-ს აყენებს.

`init_db` ცხრილებს თავიდან ქმნის და `--confirm-text RESET_DB` სჭირდება. Production-ში დამატებით `--force` უნდა გადასცე. `upgrade_db` არსებულ მონაცემს არ შლის: აკლია ცხრილს ან ცარიელ სვეტს ამატებს. `populate_db` ერთ სატესტო მოწყობილობას წერს თბილისის 120 კმ წრით, ერთ შენახულ მიწისძვრას, ერთ felt ანგარიშს და ერთ შეტყობინებას `notification_outbox`-ში. `event_id` უახლოესი გამოქვეყნებული მიწისძვრის `event.id`-ია და `earthquakes.ies_event_id`-ში ინახება. ხელახლა გაშვება იმავე ჩანაწერს არ იმეორებს.

Swagger: `http://127.0.0.1:5000/docs/`

| Method | Path | Stores |
| --- | --- | --- |
| GET | `/api/v1/devices/` | stored devices (`?limit=`) |
| GET | `/api/v1/devices/<id>` | one device |
| POST | `/api/v1/devices/` | device id, push token, language |
| GET | `/api/v1/alert-settings/` | stored alert areas (`?limit=`) |
| GET | `/api/v1/devices/<id>/alert-settings` | one device's polygon |
| PUT | `/api/v1/devices/<id>/alert-settings` | one polygon and minimum magnitude |
| GET | `/api/v1/felt-reports/` | stored felt reports (`?limit=`) |
| GET | `/api/v1/felt-reports/<id>` | one felt report |
| POST | `/api/v1/felt-reports/` | a felt report; `felt_at` is calculated on the server |
| GET, POST | `/api/v1/earthquakes/` | list earthquakes, or store a new one |
| GET, PUT, DELETE | `/api/v1/earthquakes/<event_id>` | one earthquake; PUT replaces it, DELETE removes it |
| GET | `/api/v1/notifications/stats` | totals, status counts, and counts per earthquake |
| GET | `/api/v1/notifications/` | outbox rows (`?limit=`, `event_id`, `device_id`, `status`) |
| GET | `/api/v1/notifications/<id>/attempts` | Expo attempts for one outbox row |
| POST | `/api/v1/notifications/` | `event_id` of a stored earthquake; queues recipients |
