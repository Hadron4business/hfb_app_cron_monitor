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
""" @version	19.0.1.0.2
	@owner  Hadron for Business
	@author Hadron for Business sp. z o.o.
	@date   2026.10.05

	Cron Monitor event
	One row per notable thing that happened to a scheduled action: it failed,
	it stalled, or it recovered. Also builds and sends the alert e-mail.
	Rows are written with sudo - the cron's own user may have no access here.
"""
import logging
from datetime import timedelta

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)

PARAM_DEFAULT_EMAILS = 'hfb_cron_monitor.default_emails'
PARAM_THRESHOLD_HOURS = 'hfb_cron_monitor.stalled_threshold_hours'
PARAM_RETENTION_DAYS = 'hfb_cron_monitor.retention_days'
DEFAULT_THRESHOLD_HOURS = 24
DEFAULT_RETENTION_DAYS = 90


class CronEvent(models.Model):
    _name = 'hfb.cron.event'
    _description = "Scheduled Action Monitoring Event"
    _order = 'id desc'

    cron_id = fields.Many2one(
        'ir.cron', string="Scheduled Action", required=True, readonly=True,
        ondelete='cascade', index=True)
    kind = fields.Selection([
        ('failed', "Failed"),
        ('stalled', "Stalled"),
        ('recovered', "Recovered"),
    ], string="Event", required=True, readonly=True, index=True)
    message = fields.Text(string="Message", readonly=True)
    details = fields.Text(string="Technical Details", readonly=True)
    occurrences = fields.Integer(
        string="Occurrences", default=1, readonly=True,
        help="How many times in a row the scheduled action failed; only the first failure sends an alert.")
    last_occurrence = fields.Datetime(string="Last Occurrence", readonly=True)
    notified_emails = fields.Char(string="Alert Sent To", readonly=True)
    notify_error = fields.Char(string="Alert Error", readonly=True,
                               help="Why the alert e-mail could not be created, if it could not.")

    @api.depends('cron_id', 'kind')
    def _compute_display_name(self):
        labels = dict(self._fields['kind']._description_selection(self.env))
        for event in self:
            event.display_name = "%s - %s" % (event.cron_id.name or '', labels.get(event.kind, ''))

    @api.autovacuum
    def _gc_old_events(self):
        days = self._int_param(PARAM_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
        if days <= 0:
            return
        limit = fields.Datetime.now() - timedelta(days=days)
        self.search([('create_date', '<', limit)]).unlink()

    @api.model
    def _int_param(self, key, default):
        value = self.env['ir.config_parameter'].sudo().get_param(key)
        try:
            return int(value) if value not in (None, False, '') else default
        except ValueError:
            return default

    @api.model
    def _recipients(self, cron):
        raw = cron.monitor_emails or self.env['ir.config_parameter'].sudo().get_param(PARAM_DEFAULT_EMAILS) or ''
        return tools.email_split(raw)

    @api.model
    def _register_event(self, cron, kind, message, details=False, notify=True):
        """Create the event and, for failed/stalled, e-mail the recipients."""
        event = self.sudo().create({
            'cron_id': cron.id,
            'kind': kind,
            'message': message,
            'details': details,
            'last_occurrence': fields.Datetime.now(),
        })
        if notify:
            recipients = self._recipients(cron)
            template = self.env.ref('hfb_app_cron_monitor.mail_template_cron_event', raise_if_not_found=False)
            if recipients and template:
                # Own savepoint: a broken mail must never take the event with it.
                try:
                    with self.env.cr.savepoint():
                        template.sudo().send_mail(
                            event.id, force_send=False,
                            email_values={'email_to': ','.join(recipients)})
                except Exception as e:
                    _logger.exception("Cron Monitor could not create the alert e-mail for cron #%s", cron.id)
                    event.notify_error = str(e)[:500]
                else:
                    event.notified_emails = ', '.join(recipients)
        return event

#EoF
