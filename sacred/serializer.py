import jsonpickle
import json as _json
from sacred import optional as opt

json = jsonpickle


__all__ = ("flatten", "restore")


if opt.has_numpy:
    import jsonpickle.ext.numpy as jsonpickle_numpy

    np = opt.np

    jsonpickle_numpy.register_handlers()

if opt.has_pandas:
    import jsonpickle.ext.pandas as jsonpickle_pandas

    jsonpickle_pandas.register_handlers()


jsonpickle.set_encoder_options("simplejson", sort_keys=True, indent=4)
jsonpickle.set_encoder_options("demjson", compactly=False)


def flatten(obj):
    return _json.loads(json.encode(obj, keys=True))


def restore(flat):
    return json.decode(_json.dumps(flat), keys=True, on_missing="error")
