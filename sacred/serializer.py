#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from datetime import datetime

import jsonpickle as json
from jsonpickle.handlers import BaseHandler

from sacred import optional as opt


__all__ = ('json', )


class DatetimeHandler(BaseHandler):
    def restore(self, obj):
        return obj

    def flatten(self, obj, data):
        return obj.isoformat()

DatetimeHandler.handles(datetime)

if opt.has_numpy:
    class NumpyHandler(BaseHandler):
        def flatten(self, obj, data):
            data['values'] = obj.tolist()
            data['dtype'] = str(obj.dtype)
            return data

        def restore(self, obj):
            return opt.np.array(obj["values"], dtype=obj["dtype"])

json.set_encoder_options('simplejson', sort_keys=True, indent=4)
json.set_encoder_options('demjson', compactly=False)

json.encode
