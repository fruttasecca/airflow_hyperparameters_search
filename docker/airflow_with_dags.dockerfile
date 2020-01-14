FROM puckel/docker-airflow:1.10.6-1

USER root
RUN apt-get update && apt-get install -y git wget unzip && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir scikit-learn==0.22 pandas==0.25.3 pyarrow==0.15.1
USER airflow
WORKDIR /usr/local/airflow

# this line is used so that running as
# docker build --build-arg DATE=`date +%s` ...
# will reuse the previous layers up to here and force the
# commands after here to be run again
ARG DATE=unknown

# get the dag from the repo and copy it in the airflow dags directory
RUN DATE=${DATE} \
 && mkdir /usr/local/airflow/dags \
 && git clone https://github.com/fruttasecca/airflow_hyperparameters_search.git \
 && cp airflow_hyperparameters_search/dags/* /usr/local/airflow/dags/ -r \
 && rm airflow_hyperparameters_search -r

