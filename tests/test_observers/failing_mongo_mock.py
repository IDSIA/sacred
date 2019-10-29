import mongomock
import pymongo
import pymongo.errors
from mongomock.store import DatabaseStore


class FailingMongoClient(mongomock.MongoClient):
    def __init__(
        self,
        max_calls_before_failure=2,
        exception_to_raise=pymongo.errors.AutoReconnect,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self.exception_to_raise = exception_to_raise
        self._exception_to_raise = exception_to_raise

    def get_database(
        self, name=None, codec_options=None, read_preference=None, write_concern=None
    ):
        if name is None:
            return self.get_default_database()

        db = self._database_accesses.get(name)
        if db is None:
            db_store = self._store[name]
            db = self._database_accesses[name] = FailingDatabase(
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise,
                client=self,
                name=name,
                read_preference=read_preference or self.read_preference,
                codec_options=self._codec_options,
                _store=db_store,
            )
        return db


class FailingDatabase(mongomock.Database):
    def __init__(self, max_calls_before_failure, exception_to_raise=None, **kwargs):
        super().__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self._exception_to_raise = exception_to_raise

    def get_collection(
        self,
        name,
        codec_options=None,
        read_preference=None,
        write_concern=None,
        read_concern=None,
    ):
        try:
            return self._collection_accesses[name].with_options(
                codec_options=codec_options or self._codec_options,
                read_preference=read_preference or self.read_preference,
                read_concern=read_concern,
                write_concern=write_concern,
            )
        except KeyError:
            self._ensure_valid_collection_name(name)
            collection = self._collection_accesses[name] = FailingCollection(
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise,
                database=self,
                name=name,
                write_concern=write_concern,
                read_preference=read_preference or self.read_preference,
                codec_options=codec_options or self._codec_options,
                _db_store=self._store,
            )
            return collection


class FailingCollection(mongomock.Collection):
    def __init__(self, max_calls_before_failure, exception_to_raise, **kwargs):
        super().__init__(**kwargs)
        self._max_calls_before_failure = max_calls_before_failure
        self._exception_to_raise = exception_to_raise
        self._calls = 0

    def insert_one(self, document, session=None):
        self._calls += 1
        if self._calls > self._max_calls_before_failure:
            raise pymongo.errors.ConnectionFailure
        else:
            return super().insert_one(document)

    def update_one(self, filter, update, upsert=False, session=None):
        self._calls += 1
        if self._calls > self._max_calls_before_failure:
            raise pymongo.errors.ConnectionFailure
        else:
            return super().update_one(filter, update, upsert)


class ReconnectingMongoClient(FailingMongoClient):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super().__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def get_database(
        self, name=None, codec_options=None, read_preference=None, write_concern=None
    ):
        if name is None:
            return self.get_default_database()

        db = self._database_accesses.get(name)
        if db is None:
            db_store = self._store[name]
            db = self._database_accesses[name] = ReconnectingDatabase(
                max_calls_before_reconnect=self._max_calls_before_reconnect,
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise,
                client=self,
                name=name,
                read_preference=read_preference or self.read_preference,
                codec_options=self._codec_options,
                _store=db_store,
            )
        return db


class ReconnectingDatabase(FailingDatabase):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super().__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def get_collection(
        self,
        name,
        codec_options=None,
        read_preference=None,
        write_concern=None,
        read_concern=None,
    ):
        try:
            return self._collection_accesses[name].with_options(
                codec_options=codec_options or self._codec_options,
                read_preference=read_preference or self.read_preference,
                read_concern=read_concern,
                write_concern=write_concern,
            )
        except KeyError:
            self._ensure_valid_collection_name(name)
            collection = self._collection_accesses[name] = ReconnectingCollection(
                max_calls_before_reconnect=self._max_calls_before_reconnect,
                max_calls_before_failure=self._max_calls_before_failure,
                exception_to_raise=self._exception_to_raise,
                database=self,
                name=name,
                write_concern=write_concern,
                read_preference=read_preference or self.read_preference,
                codec_options=codec_options or self._codec_options,
                _db_store=self._store,
            )
            return collection


class ReconnectingCollection(FailingCollection):
    def __init__(self, max_calls_before_reconnect, **kwargs):
        super().__init__(**kwargs)
        self._max_calls_before_reconnect = max_calls_before_reconnect

    def insert_one(self, document, session=None):
        self._calls += 1
        if self._is_in_failure_range():
            print(self.name, "insert no connection")
            raise self._exception_to_raise
        else:
            print(self.name, "insert connection reestablished")
            return mongomock.Collection.insert_one(self, document)

    def update_one(self, filter, update, upsert=False, session=None):
        self._calls += 1
        if self._is_in_failure_range():
            print(self.name, "update no connection")

            raise self._exception_to_raise
        else:
            print(self.name, "update connection reestablished")

            return mongomock.Collection.update_one(self, filter, update, upsert)

    def _is_in_failure_range(self):
        return (
            self._max_calls_before_failure
            < self._calls
            <= self._max_calls_before_reconnect
        )
