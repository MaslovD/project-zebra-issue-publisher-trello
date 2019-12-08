FROM python:3.7-alpine3.9
MAINTAINER Makrushin Egor
COPY . ./app
WORKDIR ./app
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "./app.py"]