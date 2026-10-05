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
""" @version	17.0.1.0.2
	@owner  Hadron for Business
	@author Hadron for Business sp. z o.o.
	@date   2026.10.05

	Cron Monitor settings
	Global defaults: alert recipients, stall threshold, event retention.
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cron_monitor_default_emails = fields.Char(
        string="Default Alert E-mails",
        config_parameter='hfb_cron_monitor.default_emails',
        help="Comma-separated addresses used for every scheduled action that has no alert e-mails of its own.")
    cron_monitor_threshold_hours = fields.Integer(
        string="Stalled After (hours)", default=24,
        config_parameter='hfb_cron_monitor.stalled_threshold_hours',
        help="Default for scheduled actions without their own threshold.")
    cron_monitor_retention_days = fields.Integer(
        string="Keep Events (days)", default=90,
        config_parameter='hfb_cron_monitor.retention_days',
        help="Monitoring events older than this are deleted automatically. 0 = keep forever.")

#EoF
