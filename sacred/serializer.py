#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from datetime import datetime

import jsonpickle as json
import jsonpickle.handlers


__all__ = ('json', )


class DatetimeHandler(jsonpickle.handlers.BaseHandler):
    def restore(self, obj):
        return obj

    def flatten(self, obj, data):
        return obj.isoformat()

DatetimeHandler.handles(datetime)

json.set_encoder_options('simplejson', sort_keys=True, indent=4)
json.set_encoder_options('demjson', compactly=False)
