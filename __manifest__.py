# -*- coding: utf-8 -*-
# vim: tabstop=4 softtabstop=0 shiftwidth=4 smarttab expandtab fileformat=unix
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
{
    'name': "Cron Monitor",
    'summary': "E-mail alert when a scheduled action fails or stops running",
    'description': """
Cron Monitor
============

Odoo's scheduled actions (crons) fail quietly: an exception is written to the
server log and the job simply tries again next time - nobody is told. If the
scheduler itself stops picking a job up, nobody notices either.

This app watches every scheduled action and e-mails you when:

* a scheduled action **fails** (once per failure streak, not on every retry),
* a scheduled action **stalls** - it was due more than N hours ago and still
  has not run.

Recipients and the stall threshold can be set per scheduled action, with a
global default in Settings. Every alert is also kept as an event on the
scheduled action, together with a "recovered" event when it runs fine again.
""",
    'version': "18.0.1.0.0",
    'author': "Hadron for Business sp. z o.o.",
    'website': "http://hadronforbusiness.com",
    'license': "OPL-1",
    'category': "Extra Tools",
    'depends': [
        'base_setup',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'data/ir_cron_data.xml',
        'views/cron_event_views.xml',
        'views/ir_cron_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
