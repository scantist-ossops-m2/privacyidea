# -*- coding: utf-8 -*-
#
#  2018-03-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
#  Copyright (C) 2018 Cornelius Kölbel
#  License:  AGPLv3
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
This module is used to modify counters in the database
"""
from privacyidea.models import EventCounter


def increase(counter_name):
    """
    Increase the counter value in the database.
    If the counter does not exist, yet, create the counter.

    :param counter_name: The name/identifier of the counter
    :return: the new integer value of the counter
    """
    counter = EventCounter.query.filter_by(counter_name=counter_name).first()
    if not counter:
        counter = EventCounter(counter_name, 0)
        counter.save()
    counter.increase()
    return counter.counter_value