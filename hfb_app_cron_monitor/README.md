# Cron Monitor

E-mail alert when an Odoo scheduled action (cron) **fails** or **stops running**.

## The problem

Odoo swallows exceptions raised by scheduled actions: they go to the server
log and the job simply runs again at the next interval. Nobody is notified. A
job the scheduler no longer picks up leaves no trace at all.

## How it works

- `ir.cron._callback` is wrapped: a failed job's exception is recorded and re-raised.
  The first failure of a streak creates an event and sends an alert; further failures only bump
  the event's counter. The first successful run after a failure or stall
  creates a "recovered" event.
- An hourly scheduled action (`Cron Monitor: check for stalled scheduled
  actions`) raises a "stalled" alert for every active, monitored job whose
  `nextcall` is more than the threshold in the past - one alert per missed run.
- Per scheduled action (new **Monitoring** tab): monitor on/off, alert e-mails,
  stall threshold in hours (0 = default). Global defaults in
  *Settings > General Settings > Cron Monitor*: default e-mails (empty = events
  are recorded but no mail is sent), stall threshold (24 h), event retention
  (90 days, cleaned by autovacuum).
- *Run Manually* goes through the regular job runner in Odoo 19, so manual runs are monitored too.
- If the monitor itself hits an error it never breaks the job; the last such error is kept in the
  system parameter `hfb_cron_monitor.last_error`.
- Events: *Settings > Technical > Automation > Cron Monitor Events*.

### Why events are not stored on `ir.cron`

While a job runs the scheduler holds a row lock on its `ir_cron` row from a
different database cursor, so an `UPDATE` from inside the job would wait for a
lock that is only released after the job returns. All state lives in
`hfb.cron.event`.

## Technical

- Models: `hfb.cron.event` (new), `ir.cron` and `res.config.settings` (extended).
- Hooks `ir.cron._callback(cron_name, server_action_id)`.
- Since Odoo 18 the core also counts consecutive failures (`failure_count`) and deactivates a cron
  that keeps failing for days, notifying the admin. This app complements that: it alerts on the
  *first* failure and detects jobs that are simply not being run.
- Depends on: `base_setup`, `mail`.

## Status

Ported from the 17.0 branch (see its history for the rewrite of the client-specific `hfb_cron_status`).

Tested on an Odoo 19 instance.

Polish translation (`i18n/pl.po`), store icon and banner included.
