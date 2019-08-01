from tinydb import TinyDB, Query
from tinydb.queries import QueryImpl
from hashfs import HashFS
from tinydb_serialization import Serializer, SerializationMiddleware

import sacred.optional as opt


# Set data type values for abstract properties in Serializers
series_type = opt.pandas.Series if opt.has_pandas else None
dataframe_type = opt.pandas.DataFrame if opt.has_pandas else None
ndarray_type = opt.np.ndarray if opt.has_numpy else None


class DateTimeSerializer(Serializer):
    OBJ_CLASS = dt.datetime  # The class this serializer handles

    def encode(self, obj):
        return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def decode(self, s):
        return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


class NdArraySerializer(Serializer):
    OBJ_CLASS = ndarray_type

    def encode(self, obj):
        return json.dumps(obj.tolist(), check_circular=True)

    def decode(self, s):
        return opt.np.array(json.loads(s))


class DataFrameSerializer(Serializer):
    OBJ_CLASS = dataframe_type

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s)


class SeriesSerializer(Serializer):
    OBJ_CLASS = series_type

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s, typ='series')


class FileSerializer(Serializer):
    OBJ_CLASS = BufferedReaderWrapper

    def __init__(self, fs):
        self.fs = fs

    def encode(self, obj):
        address = self.fs.put(obj)
        return json.dumps(address.id)

    def decode(self, s):
        id_ = json.loads(s)
        file_reader = self.fs.open(id_)
        file_reader = BufferedReaderWrapper(file_reader)
        file_reader.hash = id_
        return file_reader
