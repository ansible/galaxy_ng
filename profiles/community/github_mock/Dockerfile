FROM python:3
RUN mkdir -p /app
COPY requirements.txt /app/.
COPY flaskapp.py /app/.
RUN pip install -r /app/requirements.txt
RUN mkdir -p /src
RUN test -d /src/werkzeug || git clone -b SAVE_THE_STREAMS https://github.com/jctanner/werkzeug /src/werkzeug
RUN pip install -e /src/werkzeug
CMD PYTHONUNBUFFERED=1 python3 /app/flaskapp.py
