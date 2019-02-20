"""A standard machine learning task without much sacred magic."""
from sacred import Experiment
from sacred.observers import FileStorageObserver
from sklearn import svm, datasets, model_selection

ex = Experiment('svm')

ex.observers.append(
    FileStorageObserver.create("my_runs")
)
ex.add_config("config.json")


def get_model(C, gamma, kernel):
    return svm.SVC(C=C, kernel=kernel, gamma=gamma)


@ex.main  # Use automain to enable command line integration.
def run(_config):
    X, y = datasets.load_breast_cancer(return_X_y=True)
    X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y, test_size=0.2)
    clf = get_model(_config["C"], _config["gamma"], _config["kernel"])
    clf.fit(X_train, y_train)
    return clf.score(X_test, y_test)


if __name__ == "__main__":
    ex.run()
