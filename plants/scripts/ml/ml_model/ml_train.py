import numpy as np
import pandas as pd
from sklearn import (
    dummy,
    ensemble,
    gaussian_process,
    linear_model,
    naive_bayes,
    neighbors,
    neural_network,
    svm,
    tree,
)
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import GridSearchCV, GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.utils._testing import ignore_warnings  # noqa

from ml_helpers.preprocessing.features import FeatureContainer
from plants.scripts.ml.ml_model.ml_pipeline import create_pipeline


def apply_grid_search(
    x: pd.DataFrame, y: pd.Series, pipeline: Pipeline, param_grid: dict
) -> Pipeline:
    """"""
    n_groups = 3  # test part will be 1/n
    n_splits = 3  # k-fold will score n times; must be <= n_groups
    np.random.seed(42)
    kfold_groups = np.random.randint(n_groups, size=len(x))
    group_kfold = GroupKFold(n_splits=n_splits)

    search = GridSearchCV(
        pipeline,
        param_grid=param_grid,
        cv=group_kfold,
        scoring="f1",
        refit="f1",  # at the end, refit the best estimator on the whole dataset as
        # best_estimator_
    )
    search.fit(X=x, y=y, groups=kfold_groups)
    print(f'{"Best params:": <45.45}{search.best_params_}')
    print(f'{"Score of refitted model with full dataset:": <45.45}{search.best_score_}')

    # compare with dummy classifier always predicting the most frequent class
    dummy_classifier = DummyClassifier()
    dummy_classifier.fit(x, y)
    dummy_scores = cross_val_score(
        estimator=dummy_classifier,
        X=x,
        y=y,
        groups=kfold_groups,
        scoring="f1",
        cv=group_kfold,
    )
    print(f'{"Score of dummy classifier:": <45.45}{np.mean(dummy_scores)}')

    return search.best_estimator_
    # df_results = pd.DataFrame(search.cv_results_)  # noqa
    # preprocessor = pipeline.steps[0][1]
    # preprocessor.fit(x)
    # columns, df_t = get_transformed_df_from_column_transformer(preprocessor, x)


def _try_classifiers(x, y, feature_container: FeatureContainer):
    n_groups = 3  # test part will be 1/n
    n_splits = 3  # k-fold will score n times; must be <= n_groups
    np.random.seed(42)
    kfold_groups = np.random.randint(n_groups, size=len(x))
    group_kfold = GroupKFold(n_splits=n_splits)

    models = [
        dummy.DummyClassifier(),
        linear_model.RidgeClassifier(),
        linear_model.RidgeClassifierCV(),
        linear_model.Lasso(),
        linear_model.LassoCV(),
        linear_model.BayesianRidge(),
        linear_model.SGDClassifier(),
        linear_model.LogisticRegression(),
        linear_model.LogisticRegressionCV(),
        svm.SVC(),
        svm.LinearSVC(),
        neighbors.NearestNeighbors(),
        neighbors.KNeighborsClassifier(),
        gaussian_process.GaussianProcessClassifier(),
        naive_bayes.GaussianNB(),
        # naive_bayes.CategoricalNB(),
        tree.DecisionTreeClassifier(),
        ensemble.RandomForestClassifier(),
        ensemble.AdaBoostClassifier(),
        ensemble.GradientBoostingClassifier(),
        ensemble.BaggingClassifier(),
        neural_network.MLPClassifier(),
    ]

    results = {}
    for model in models:
        pipeline = create_pipeline(feature_container=feature_container, model=model)
        with ignore_warnings(category=(ConvergenceWarning, UserWarning)):
            scores = cross_val_score(
                estimator=pipeline,
                X=x,
                y=y,
                groups=kfold_groups,
                scoring="f1",
                cv=group_kfold,
            )
        print(f'{"Score of " + str(model) + ":": <45.45}{np.mean(scores)}')
        results[str(model)] = np.mean(scores)

    df_results = pd.Series(results).to_frame().sort_values(0, ascending=False)
    print(df_results)


def optimize_knn_classifier(x, y, feature_container: FeatureContainer):
    """Optimize KNN classifier."""
    pipeline = create_pipeline(
        feature_container=feature_container, model=neighbors.KNeighborsClassifier()
    )
    param_grid = {
        "estimator__n_neighbors": [1, 3, 5, 8, 10],  # default 5
        "estimator__weights": ["uniform", "distance"],  # default 'uniform'
        "estimator__algorithm": [
            "auto",
            "ball_tree",
            "kd_tree",
            "brute",
        ],  # default 'auto'
        "estimator__leaf_size": [10, 20, 30, 50],  # default 30
        "estimator__p": [1, 2],  # default 2
    }
    with ignore_warnings(category=(FutureWarning, UserWarning)):
        trained_pipeline = apply_grid_search(
            pipeline=pipeline, x=x, y=y, param_grid=param_grid
        )
        print(trained_pipeline)
    # Results:
    # {'estimator__algorithm': 'ball_tree', 'estimator__leaf_size': 20,
    # 'estimator__n_neighbors': 10,
    # 'estimator__p': 2, 'estimator__weights': 'distance'} has an F1 of 0.60


def cv_classifier(x, y, pipeline: Pipeline):
    n_groups = 3  # test part will be 1/n
    n_splits = 3  # k-fold will score n times; must be <= n_groups
    np.random.seed(42)
    kfold_groups = np.random.randint(n_groups, size=len(x))
    group_kfold = GroupKFold(n_splits=n_splits)
    with ignore_warnings(category=(ConvergenceWarning, UserWarning)):
        scores = cross_val_score(
            pipeline, x, y, cv=group_kfold, groups=kfold_groups, scoring="f1"
        )
    print(f"Scores: {scores}")
    print(f"Mean score: {np.mean(scores)}")


def optimize_randomforest_classifier(x, y, feature_container: FeatureContainer):
    """Optimize a RandomForest classifier."""
    pipeline = create_pipeline(
        feature_container=feature_container, model=ensemble.RandomForestClassifier()
    )
    param_grid = {
        "estimator__n_estimators": [2, 5, 8, 10, 30],  # default 100 -> 5
        "estimator__max_depth": [None, 1, 3, 10, 20],  # default None # -> None
        "estimator__min_samples_split": [
            0.01,
            0.3,
            0.6,
            1.0,
            2,
            3,
        ],  # default 2 (abs.) -> 0.01
        "estimator__min_samples_leaf": [1, 2, 4],  # default 1 -> 1
        "estimator__min_weight_fraction_leaf": [0.0, 0.2, 0.5],  # default 0.0 -> 0.0
        "estimator__max_features": ["sqrt", "log2", None],  # default 'sqrt' -> None
        "estimator__min_impurity_decrease": [0.0, 0.02],  # default 0.0 -> 0.0
        "estimator__ccp_alpha": [0.0, 0.02],  # default 0.0 -> 0.0
        "estimator__max_samples": [
            None,
            0.1,
            0.3,
            0.5,
            0.7,
            0.9,
            1,
            10,
            30,
            100,
            300,
        ],  # default None -> None
    }
    with ignore_warnings(category=(FutureWarning, UserWarning)):
        trained_pipeline = apply_grid_search(
            pipeline=pipeline, x=x, y=y, param_grid=param_grid
        )
        print(trained_pipeline)
    # Results:
    # {'estimator__n_estimators': 5, 'estimator__min_samples_split': 0.01,
    # 'estimator__max_features': None}
    # has an F1 of 0.49
