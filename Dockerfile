# # Use the official Python image
# # FROM stac-utils/stac-fastapi-os
# FROM python:3-slim-buster

# # Set the working directory
# WORKDIR /app
# # Copy the application code
# COPY . .

# WORKDIR /app/stac_fastapi/elasticsearch

# # Copy the requirements file
# # COPY requirements.txt .

# # TODO USERADD AND USER

# # Install the dependencies
# # RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install -e .

# # Expose the port your app runs on
# EXPOSE 8080

# # Specify the command to run your application
# # CMD ["python", "main.py", "--root-path", "/geospatial/api"]
# CMD ["python","-m","stac_fastapi.elasticsearch.app"]
# # , "--root-path", "/geospatial/search/stac"]

FROM python:3.10-slim

RUN apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install gcc && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# set ES API KEY as env so it's not in the iac template (TODO: use secrets into iac)
ENV ES_API_KEY=$ES_API_KEY

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -e ./stac_fastapi/core
RUN pip install --no-cache-dir ./stac_fastapi/elasticsearch[server,docs]

EXPOSE $APP_PORT

CMD ["uvicorn", "stac_fastapi.elasticsearch.app:main_app", "--host", "$APP_HOST", "--port", $APP_PORT]