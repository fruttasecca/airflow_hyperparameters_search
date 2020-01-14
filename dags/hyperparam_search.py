import os
from functools import reduce
import ast
from sklearn.model_selection import ParameterGrid
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import redis
import pyarrow
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime

__DATASET_REDIS_KEY = "HTRU2"
__OUTPUT_QUEUE = "hyperparam_search_OUTPUT_QUEUE"

for name in ["REDIS_HOST", "REDIS_PORT"]:
    assert name in os.environ, "%s environment variable is missing." % name


def prepare_data():
    """
    Download data and put in redis as a serialized dataframe.
    :return:
    """
    print("downloading data")
    os.system("wget https://archive.ics.uci.edu/ml/machine-learning-databases/00372/HTRU2.zip && unzip HTRU2.zip")

    print("importing data")
    df = pd.read_csv("HTRU_2.csv", header=None)

    print("connecting to redis and loading data")
    redis_c = redis.Redis(host=os.environ["REDIS_HOST"], port=os.environ["REDIS_PORT"], charset="utf-8")
    context = pyarrow.default_serialization_context()
    redis_c.set(__DATASET_REDIS_KEY, context.serialize(df).to_buffer().to_pybytes())

    print("cleaning up")
    os.system("rm HTRU_2.csv rm HTRU2.zip HTRU_2.arff Readme.txt")


def test_hyperparams(hyperparameters):
    """
    Test the given hyperparameters and put the hyperparameters with
    the evaluation score in the output queue.
    :param hyperparameters:
    :return:
    """
    print("connecting to redis and getting data")
    redis_c = redis.Redis(host=os.environ["REDIS_HOST"], port=os.environ["REDIS_PORT"], charset="utf-8")
    context = pyarrow.default_serialization_context()
    df = context.deserialize(redis_c.get(__DATASET_REDIS_KEY))

    print("computing result")
    clf = RandomForestClassifier(**hyperparameters)
    scores = cross_val_score(clf, df.loc[:, df.columns != 8], df[8], cv=10, scoring="f1")
    hyperparameters["score"] = scores.mean()

    print("pushing to %s " % __OUTPUT_QUEUE)
    redis_c.lpush(__OUTPUT_QUEUE, str(hyperparameters))


def aggregate_results():
    """
    Aggregate results from the output queue and keep the hyperparameters that provided
    the best score.
    :return:
    """
    print("connecting to redis and retrieveing results")
    redis_c = redis.Redis(host=os.environ["REDIS_HOST"], port=os.environ["REDIS_PORT"], charset="utf-8")

    # retrieve results and keep the best hyperparameters
    results = redis_c.lrange(__OUTPUT_QUEUE, 0, - 1)
    results = [ast.literal_eval(res.decode("utf-8")) for res in results]
    redis_c.delete(__OUTPUT_QUEUE)
    redis_c.delete(__DATASET_REDIS_KEY)
    best_params = reduce(lambda x, y: x if x["score"] >= y["score"] else y, results)
    print("Best returned parameters")
    print(best_params)


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    # 'email': "myemail"
    # "email_on_failure": True,
}

dag = DAG('hyperparam_search', default_args=default_args,
          schedule_interval=None,
          start_date=datetime(2020, 1, 12),
          concurrency=4,
          max_active_runs=1)

# download data, store it
preparation = PythonOperator(dag=dag,
                             task_id='prepare_data',
                             provide_context=False,
                             python_callable=prepare_data
                             )

# operator to aggregate all results
aggregation = PythonOperator(dag=dag,
                             task_id='aggregate_results',
                             provide_context=False,
                             python_callable=aggregate_results
                             )

# 1 task for each hyperparameter set
param_grid = dict()
param_grid["n_estimators"] = [100]
param_grid["criterion"] = ["gini", "entropy"]
param_grid["max_depth"] = [None, 2, 4]
param_grid["max_features"] = ["auto", "log2", None]
param_grid["bootstrap"] = [True, False]
param_grid["ccp_alpha"] = [0., 0.32]
param_grid["random_state"] = [0]
param_grid["n_jobs"] = [1]

for index, parameters in enumerate(ParameterGrid(param_grid)):
    computation = PythonOperator(dag=dag,
                                 task_id="test_hyperparams_%s" % index,
                                 provide_context=False,
                                 python_callable=test_hyperparams,
                                 op_kwargs={"hyperparameters": parameters}
                                 )

    computation.set_upstream(preparation)
    aggregation.set_upstream(computation)
