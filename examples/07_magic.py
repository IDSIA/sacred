"""A standard machine learning task using sacred's magic."""
from sacred import Experiment
from sacred.observers import FileStorageObserver
from sklearn import svm, datasets, model_selection

ex = Experiment("svm")

ex.observers.append(FileStorageObserver("my_runs"))


@ex.config  # Configuration is defined through local variables.
def cfg():
    C = 1.0
    gamma = 0.7
    kernel = "rbf"
    seed = 42


@ex.capture
def get_model(C, gamma, kernel):
    return svm.SVC(C=C, kernel=kernel, gamma=gamma)


@ex.automain  # Using automain to enable command line integration.
def run():
    X, y = datasets.load_breast_cancer(return_X_y=True)
    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        X, y, test_size=0.2
    )
    clf = get_model()  # Parameters are injected automatically.
    clf.fit(X_train, y_train)
    return clf.score(X_test, y_test)
