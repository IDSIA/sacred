#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import jsonpickle as json
from jsonpickle.handlers import BaseHandler
import json as _json

from sacred import optional as opt

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('flatten', 'restore')


# class DatetimeHandler(BaseHandler):
#     def restore(self, obj):
#        return datetime.datetime.strptime(obj['date'], "%Y-%m-%dT%H:%M:%S.%f")
#
#     def flatten(self, obj, data):
#         data['date'] = obj.isoformat()
#         return data
#
# DatetimeHandler.handles(datetime.datetime)

if opt.has_numpy:
    np = opt.np

    class NumpyArrayHandler(BaseHandler):
        def flatten(self, obj, data):
            data['values'] = obj.tolist()
            data['dtype'] = str(obj.dtype)
            return data

        def restore(self, obj):
            return opt.np.array(obj["values"], dtype=obj["dtype"])

    class NumpyGenericHandler(BaseHandler):
        def flatten(self, obj, data):
            return np.asscalar(obj)

        def restore(self, obj):
            return obj

    NumpyArrayHandler.handles(np.ndarray)
    for t in [np.bool_, np.int_, np.float_, np.intc, np.intp, np.int8,
              np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32,
              np.uint64, np.float16, np.float32, np.float64]:
        NumpyGenericHandler.handles(t)


if opt.has_pandas:
    import pandas as pd

    class PandasDataframeHandler(BaseHandler):
        def flatten(self, obj, data):
            # TODO: this is slow
            data['values'] = json.loads(obj.to_json())
            data['dtypes'] = {k: str(v) for k, v in dict(obj.dtypes).items()}
            return data

        def restore(self, obj):
            # TODO: get rid of unnecessary json.dumps
            return pd.read_json(json.dumps(obj['values']),
                                dtype=obj['dtypes'])

    PandasDataframeHandler.handles(pd.DataFrame)

json.set_encoder_options('simplejson', sort_keys=True, indent=4)
json.set_encoder_options('demjson', compactly=False)


def flatten(obj):
    return _json.loads(json.encode(obj, keys=True))


def restore(flat):
    return json.decode(_json.dumps(flat), keys=True)
