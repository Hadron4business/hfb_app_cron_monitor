# Cron Monitor

E-mail alert when an Odoo scheduled action (cron) **fails** or **stops running**.

## The problem

Odoo swallows exceptions raised by scheduled actions: they go to the server
log and the job simply runs again at the next interval. Nobody is notified. A
job the scheduler no longer picks up leaves no trace at all.

## How it works

- `ir.cron._handle_callback_exception` is overridden to remember the exception
  and `ir.cron._callback` to evaluate it once the job returns. The first failure
  of a streak creates an event and sends an alert; further failures only bump
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
- **Only runs started by the scheduler are monitored.** *Run Manually* does not go through
  `_callback` in Odoo 17 - the error is shown straight in the browser and nothing is recorded.
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
- Written for the Odoo 17 `_callback(cron_name, server_action_id, job_id)`
  signature; this changes in later series (see the porting notes before
  adapting).
- Depends on: `base_setup`, `mail`.

## Status

Built from the client-specific `hfb_cron_status` module, rewritten: the original
never recorded successful runs (its `_callback` returned before the logging
code) and would have deadlocked on the `ir_cron` row lock.

Tested on an Odoo 17 instance (failure, repeated failure, recovery, stalled job, monitoring switched off).

Polish translation (`i18n/pl.po`), store icon and banner included.
