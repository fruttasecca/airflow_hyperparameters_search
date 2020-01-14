# airflow_hyperparameters_search
Quick setup for a dockerized and scalable hyperparameter search for ML models using airflow.

#### What this is
Something simple I've come up with
to try out airflow. It allows to distribute
the training of multiple models, can serve
as a starting point to anyone having the same
need.  

Based on two docker files:
- docker/airflow_with_dags.dockerfile: the airflow container
image extended with the needed dependencies to run the model.  
After
installing dependencies it will pull this very
repository and put in the correct directory the DAG
that you can find in /dags.  
If you use something different than sklearn or intend
to run your own dags, this is the file to change.
- docker/docker-compose.yml: the compose file that spins
everything up.  
Services: redis, postgres, airflow webserver, [flower](https://flower.readthedocs.io/en/latest/),
the airflow scheduler, and the airflow worker. The only service
that you should scale is the worker, to scale the number of workers
you are using.

The defined DAG is comprised of a task which downloads a classification
dataset, followed by N tasks trying out different hyperparameters
of a sklearn model, followed by an aggregation task which collects
results and prints the best found hyperparameters.

#### How to try out from scratch:
1) Go in /docker and run  
``docker-compose up``
3) Launch the DAG from the web interface at 127.0.0.1:9080 by
unpausing it and then triggering it.

#### How to use this for yourself:
1) Define your DAG (dags/hyperparam_search.py can serve as a starting point).
2) Build your image by modifying docker/airflow_with_dags.dockerfile accordingly. If
you push new DAGS and want to rebuild to pull DAGs from your repository
without rebuilding the whole image I suggest to use  
``docker build --build-arg DATE=`date +%s` -f airflow_with_dags.dockerfile .``
3) Launch by going in /docker and using `docker-compose up` or  
`docker stack deploy --compose-file=docker-compose.yml flow`
4) Keep track of progress on the airflow web interface at 127.0.0.1:9080 and
of the workers at the flower web interface at 127.0.0.1:9081. From the airflow
web interface you get read whatever you print from a task, i.e. the best found
hyperparameters.