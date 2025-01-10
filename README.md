# GW Treasure Map 
Website environment

## Requirements

### Python:
 * Python Version 3.11

### Python Libraries
(that you will probably have to `pip3 install`)

```
python -m pip install -r requirements.txt
```

### Configuration
Configuration is handled via environmental variables. At a minimum, the following env vars must be
present:

    DB_PWD
    MAIL_PASSWORD
    RECAPTCHA_PUBLIC_KEY
    RECAPTCHA_PRIVATE_KEY
    ZENODO_ACCESS_KEY
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    REDIS_URL
    ...

See [gwtmconfig.py](src/gwtmconfig.py) for other configration options and defaults for other values.

Env vars can be set by using export:

```bash
export MAIL_PASSWORD=ASecretPassword
export RECAPTCHA_PUBLIC_KEY=ASecretPassword2
```
Or by using a utility like [direnv](https://direnv.net).

### Running the application and dependencies locally

1. Build the docker image
```bash
docker build -t gwtm_web .
```
2. Set mimimum required environment variables: DB_USER, DB_PWD, DB_NAME.
3. Run the docker image using docker-compose:
```bash
docker-compose up -d
```
4. The application should now be running on localhost:8080.

Note that the provided docker compose creates an empty database. 

**TO DO** - Add some sample data to the database before starting the app.

### Running tests

Tests can be run from the root directory using pytest. First create a virtual environment and install the requirements:

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

Then run the tests:
```
pytest
```

### Running Redis

Redis is a fast in memory key/value store. It is used in this project for both caching
and as a message broker for the Celery task worker (next section).

Running redis with Docker is easy:

```bash
docker run --name redis -p6379:6379 -d redis
```

This will start a server listening on localhost:6379, which is the default value Treasuremap will
look for, so no other configuration should be necessary.

### Running the Celery worker

In order to run certain code off the main HTTP thread we use celery to be able to run tasks in the background.
This requires Redis to be running (previous section).

Once redis is up, we can start a worker:

```bash
celery -A src.tasks.celery worker
```

You can test this is working but using the probability calculator for an event.


### Running the application in production
The application can be built and deployed as a docker image.

To build the image only, use the build command:

`docker build -t gwtm_web .`

To deploy an image, it first must be pushed up to the Elastic Cloud Registry endpoint. First, tag
the image with the repository name:

`docker tag gwtm_web:latest 929887798640.dkr.ecr.us-east-2.amazonaws.com/gwtreasuremap:latest`

Then make sure you are logged into the registry:

`./ecrlogin.sh`

Finally, push the image:

`docker push 929887798640.dkr.ecr.us-east-2.amazonaws.com/gwtreasuremap:latest`

Now, log into the Amazon dashboard and navigate to the ECS (Elastic Container Service).
Find the Tasks Definitions section and create a new revision of gwtm_web. Leave
all the values as they are, unless there is something specific about the deployment that you want to change.

Once the new task is created, go the gwtmweb [service definition](https://us-east-2.console.aws.amazon.com/ecs/v2/clusters/default/services/gwtmweb/edit?region=us-east-2)
and edit it, changing the revision of the task to the latest one (the one we just created).
After clicking update, the service should pull the new image and deploy the new version of the code.
