FROM python:alpine

WORKDIR /src
COPY src .
RUN pip install -r requirements.txt
CMD [ "python", "main.py" ]