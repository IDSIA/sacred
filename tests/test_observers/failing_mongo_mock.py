import mongomock
import pymongo
import pymongo.errors


class FailingMongoClient(mongomock.MongoClient):
    def __init__(self, max_calls_before_failure=2,
                 exception_to_raise=pymongo.errors.AutoReconnect, **kwargs):
        super(FailingMongoClient, self).__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self.exception_to_raise = exception_to_raise
        self._exception_to_raise = exception_to_raise

    def get_database(self, name, codec_options=None, read_preference=None,
                     write_concern=None):
        db = self._databases.get(name)
        if db is None:
            db = self._databases[name] = FailingDatabase(
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise, client=self,
                name=name, )
        return db


class FailingDatabase(mongomock.Database):
    def __init__(self, max_calls_before_failure, exception_to_raise=None,
                 **kwargs):
        super(FailingDatabase, self).__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self._exception_to_raise = exception_to_raise

    def get_collection(self, name, codec_options=None, read_preference=None,
                       write_concern=None):
        collection = self._collections.get(name)
        if collection is None:
            collection = self._collections[name] = FailingCollection(
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise, db=self,
                name=name, )
        return collection


class FailingCollection(mongomock.Collection):
    def __init__(self, max_calls_before_failure, exception_to_raise, **kwargs):
        super(FailingCollection, self).__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self._exception_to_raise = exception_to_raise
        self._calls = 0

    def insert_one(self, document):
        self._calls += 1
        if self._calls > self._max_calls_before_failure:
            raise pymongo.errors.ConnectionFailure
        else:
            return super(FailingCollection, self).insert_one(document)

    def update_one(self, filter, update, upsert=False):
        self._calls += 1
        if self._calls > self._max_calls_before_failure:
            raise pymongo.errors.ConnectionFailure
        else:
            return super(FailingCollection, self).update_one(filter, update,
                                                             upsert)


class ReconnectingMongoClient(FailingMongoClient):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super(ReconnectingMongoClient, self).__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def get_database(self, name, codec_options=None, read_preference=None,
                     write_concern=None):
        db = self._databases.get(name)
        if db is None:
            db = self._databases[name] = ReconnectingDatabase(
                max_calls_before_reconnect=self._max_calls_before_reconnect,
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise, client=self,
                name=name, )
        return db


class ReconnectingDatabase(FailingDatabase):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super(ReconnectingDatabase, self).__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def get_collection(self, name, codec_options=None, read_preference=None,
                       write_concern=None):
        collection = self._collections.get(name)
        if collection is None:
            collection = self._collections[name] = ReconnectingCollection(
                max_calls_before_reconnect=self._max_calls_before_reconnect,
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise, db=self,
                name=name, )
        return collection


class ReconnectingCollection(FailingCollection):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super(ReconnectingCollection, self).__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def insert_one(self, document):
        self._calls += 1
        if self._is_in_failure_range():
            print(self.name, "insert no connection")
            raise self._exception_to_raise
        else:
            print(self.name, "insert connection reestablished")
            return mongomock.Collection.insert_one(self, document)

    def update_one(self, filter, update, upsert=False):
        self._calls += 1
        if self._is_in_failure_range():
            print(self.name, "update no connection")

            raise self._exception_to_raise
        else:
            print(self.name, "update connection reestablished")

            return mongomock.Collection.update_one(self, filter, update,
                                                   upsert)

    def _is_in_failure_range(self):
        return (self._max_calls_before_failure
                < self._calls
                <= self._max_calls_before_reconnect)
