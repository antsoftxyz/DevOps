FROM python:alpine

WORKDIR /src
COPY src .
RUN pip install -r requirements.txt
CMD [ "python", "main.py" ]

ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION
LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="portainer-api" \
      org.label-schema.description="A SignalR project for quote." \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$BUILD_VERSION \
      org.label-schema.vcs-url="https://github.com/antsoftxyz/DevOps"