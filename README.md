# HipKarma

Karma system for Hipchat. Can be installed to a HipChat room as an Add-On.


## Usage

Install HipKarma on a room in HipChat by entering the URL of the capabilities descriptor (`/karma/capabilities`) on
HipChat's configuration page.

Give karma by sending a message in a room which HipChat is installed on like this:

```
@phone++ #writing an awesome karma add-on
```

You can also give karma to something that's not a user, just don't use `@`. The comment is optional.

Show karma for a user like this:

```
@karma show phone
```

## Configuration

The following environment variables can optionally be set in `.env` (for running locally) or with heroku config:set
(for running on heroku):
* `ADDON_NAME`: The name of the Add-On
* `ADDON_CHAT_NAME`: The name to use for sending HipChat messages
* `ADDON_KEY`: The unique key for this application on HipChat
* `DJANGO_DEBUG`: Set to any string to enable debug mode, unset to turn off. This should never be set in production.
* `SECRET_KEY`: The secret key for Django to use. If not set a default will be used, but this should always be set to a
random string in production.
* `DATABASE_URL`: The URL of the database to use for storage.

## Running Locally

Make sure you have Python [installed properly](http://install.python-guide.org). Also, install the
[Heroku Toolbelt](https://toolbelt.heroku.com/).

```sh
$ git clone git@github.com:heroku/python-getting-started.git
$ cd python-getting-started
$ pip install -r requirements.txt
$ python manage.py syncdb
$ foreman start web
```

Your app should now be running on [localhost:5000](http://localhost:5000/). You can use [`ngrok`](http://ngrok.com) to make
your server accessible from the internet, allowing webhooks to function.

## Deploying to Heroku

```sh
$ heroku create
$ git push heroku master
$ heroku run python manage.py syncdb
$ heroku open
```

