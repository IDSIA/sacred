FROM python:3.6-jessie

RUN apt update \
   && pip install https://github.com/chovanecm/sacredboard/archive/develop.zip \
   && rm -rf /var/lib/apt/lists/*

ENTRYPOINT sacredboard -mu mongodb://$MONGO_INITDB_ROOT_USERNAME:$MONGO_INITDB_ROOT_PASSWORD@mongo:27017/?authMechanism=SCRAM-SHA-1 $MONGO_DATABASE
