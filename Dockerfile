FROM python:3.7

LABEL maintainer="Oliver Rod <ol.rod@ostfalia.de>"
ENV PYTHONUNBUFFERED 1
# create directory which can be a place for generated static content
# volume can be used to serve these files with a webserver
RUN mkdir -p /var/www/static
VOLUME /var/www/static

# create directory for application source code
# volume can be used for live-reload during development
RUN mkdir -p /usr/django/middleware
# VOLUME /usr/django/middleware

# set default port for gunicorn
ENV PORT=8000

# install gettext > Internationalisierung
RUN apt-get update -yqq && apt-get install -y gettext

# install django
ENV DJANGO_VERSION=2.0.7

RUN apt-get update && \
 apt-get install -y && \
 apt-get install -y subversion && \
 pip install --upgrade pip && \
 apt-get autoremove -y

RUN mkdir /middleware
ADD ["./requirements.txt", "./middleware/config/"]
RUN pip install -r /middleware/config/requirements.txt \
    pip install uwsgi

# Run uwsgi unpriviledged
RUN groupadd uwsgi && useradd -g uwsgi uwsgi

# supervisor ?
ADD [".","/middleware/"]

COPY api/ api/
COPY proforma/ proforma/
COPY taskget/ taskget/


RUN chown -R uwsgi:uwsgi /middleware

WORKDIR /middleware/proforma

EXPOSE 8000
#CMD [ "/usr/local/bin/python", "/praktomat/src/manage.py", "runserver", "0.0.0.0:8000"]
CMD [ "uwsgi", "--ini", "/usr/django/middleware/uwsgi.ini"]
#CMD [ "uwsgi", "--http 0.0.0.0:8080", \
#               "--http-to /tmp/uwsgi.sock",\
#               "--wsgi", "main:application" ]