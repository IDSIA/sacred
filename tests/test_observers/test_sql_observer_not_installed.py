import pytest
from sacred.optional import has_sqlalchemy
from sacred.observers import SqlObserver
from sacred import Experiment


@pytest.fixture
def ex():
    return Experiment("ator3000")


@pytest.mark.skipif(has_sqlalchemy, reason="We are testing the import error.")
def test_importerror_sql(ex):
    with pytest.raises(ImportError):
        ex.observers.append(SqlObserver("some_uri"))

        @ex.config
        def cfg():
            a = {"b": 1}

        @ex.main
        def foo(a):
            return a["b"]

        ex.run()
