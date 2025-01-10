FROM python:3.11

WORKDIR /app

ENV PYTHONBUFFERED 1

RUN pip install --upgrade pip
COPY ./requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD ["gunicorn", "-b", "0.0.0.0:8080", "src.api_v1:app", "-t", "1000"]

