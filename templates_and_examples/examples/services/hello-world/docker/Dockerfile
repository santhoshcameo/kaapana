FROM local-only/base-python-alpine:latest

LABEL IMAGE="hello-world"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

WORKDIR /app

# RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
# RUN pip install psycopg2

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]