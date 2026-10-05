# -*- coding: utf-8 -*-
#################################################################################
#
# Odoo, Open Source Management Solution
# Copyright (C) 2017-2026 Hadron for Business sp. z o.o. (http://hadronforbusiness.com)
#
# This program is proprietary software, licensed under the Odoo Proprietary
# License v1.0 (OPL-1). Its use is governed by the Odoo Apps terms available
# at https://www.odoo.com/documentation/user/legal/licenses.html and the
# license agreement accepted at purchase / installation.
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the
# Software or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in
# all copies or substantial portions of the Software.
#
#################################################################################
""" @version	17.0.1.0.3
	@owner  Hadron for Business
	@author Hadron for Business sp. z o.o.
	@date   2026.10.05

	Cron Monitor - scheduled action hooks
	Hooks into the cron runner. Odoo's _callback swallows job exceptions itself
	(it calls _handle_callback_exception), so failures are caught there and
	evaluated once _callback returns.

	Status is deliberately NOT written to the ir_cron row: while a job runs, the
	scheduler holds a row lock on it from another cursor, so an UPDATE from inside
	the job would wait for a lock that is only released after the job returns.
	Everything is stored in hfb.cron.event instead.
"""
import logging
import threading
import traceback
from datetime import timedelta

from odoo import SUPERUSER_ID, _, api, fields, models

from .cron_event import DEFAULT_THRESHOLD_HOURS, PARAM_THRESHOLD_HOURS

_logger = logging.getLogger(__name__)

# One cron job runs per thread, so the exception handed to
# _handle_callback_exception can be passed to _callback through thread-local.
_local = threading.local()


class IrCron(models.Model):
    _inherit = 'ir.cron'

    monitor_enabled = fields.Boolean(
        string="Monitor this action", default=True,
        help="Send an alert when this scheduled action fails or stops running.")
    monitor_emails = fields.Char(
        string="Alert E-mails",
        help="Comma-separated addresses. Leave empty to use the default addresses from Settings.")
    monitor_threshold_hours = fields.Integer(
        string="Stalled After (hours)", default=0,
        help="Raise an alert when the action was due this many hours ago and still has not run. "
             "0 = use the default from Settings.")
    event_ids = fields.One2many('hfb.cron.event', 'cron_id', string="Monitoring Events", copy=False)

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        _local.failure = None
        result = super()._callback(cron_name, server_action_id, job_id)
        failure, _local.failure = getattr(_local, 'failure', None), None
        self._monitor_record_run(job_id, failure)
        return result

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        _local.failure = job_exception
        return super()._handle_callback_exception(cron_name, server_action_id, job_id, job_exception)

    @api.model
    def _monitor_record_run(self, job_id, failure):
        """Never let the monitor itself break a job: any problem is only logged."""
        try:
            with self.env.cr.savepoint():
                cron = self.sudo().browse(job_id).exists()
                if not cron or not cron.monitor_enabled:
                    return
                Event = self.env['hfb.cron.event'].sudo()
                last = Event.search([('cron_id', '=', cron.id)], limit=1)
                if failure is not None:
                    message = ("%s: %s" % (type(failure).__name__, failure))[:2000]
                    if last and last.kind == 'failed':
                        last.write({
                            'occurrences': last.occurrences + 1,
                            'message': message,
                            'last_occurrence': fields.Datetime.now(),
                        })
                    else:
                        details = ''.join(traceback.format_exception(
                            type(failure), failure, failure.__traceback__))[-8000:]
                        Event._register_event(cron, 'failed', message, details=details)
                elif last and last.kind in ('failed', 'stalled'):
                    Event._register_event(cron, 'recovered', _("The scheduled action ran successfully again."),
                                    notify=False)
        except Exception as e:
            _logger.exception("Cron Monitor could not record the run of cron job #%s", job_id)
            self._monitor_store_error("run of cron job #%s: %s" % (job_id, e))

    @api.model
    def _monitor_store_error(self, message):
        """Keep the last internal error where an admin without server-log access can read it
        (system parameter hfb_cron_monitor.last_error). Own cursor: the current transaction
        may be in a bad state."""
        try:
            with self.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['ir.config_parameter'].set_param(
                    'hfb_cron_monitor.last_error', "%s UTC - %s" % (fields.Datetime.now(), message[:1500]))
        except Exception:
            _logger.exception("Cron Monitor could not store its last error")

    @api.model
    def _check_stalled_crons(self):
        """Called hourly by the 'Cron Monitor: check for stalled scheduled actions' job.
        A job is stalled when its next call is more than the threshold in the past;
        one alert is raised per missed run."""
        Event = self.env['hfb.cron.event'].sudo()
        now = fields.Datetime.now()
        default_hours = Event._int_param(PARAM_THRESHOLD_HOURS, DEFAULT_THRESHOLD_HOURS)
        crons = self.sudo().search([
            ('active', '=', True),
            ('monitor_enabled', '=', True),
            ('nextcall', '<', now - timedelta(hours=1)),
        ])
        for cron in crons:
            hours = cron.monitor_threshold_hours or default_hours
            if cron.nextcall >= now - timedelta(hours=hours):
                continue
            last = Event.search([('cron_id', '=', cron.id)], limit=1)
            if last and last.kind == 'stalled' and last.create_date >= cron.nextcall:
                continue
            try:
                with self.env.cr.savepoint():
                    Event._register_event(cron, 'stalled', _(
                        "Scheduled action '%(name)s' was due at %(due)s (UTC) and has not run for more than %(hours)s hours.",
                        name=cron.name, due=cron.nextcall, hours=hours))
            except Exception as e:
                _logger.exception("Cron Monitor could not raise a stalled alert for cron #%s", cron.id)
                self._monitor_store_error("stalled alert for cron #%s: %s" % (cron.id, e))

#EoF
