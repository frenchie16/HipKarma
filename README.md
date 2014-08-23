# HipKarma

Karma system for Hipchat

## Configuration

The following environment variables should be set in `.env` (for running locally) or with heroku config:set (for running on heroku):
* `HIPCHAT_TOKEN`: your auth token for HipChat
* `ROOMS`: a pipe-separated list of rooms (listed by name or by ID) in which karma should be tracked.

## Running Locally

Make sure you have Python [installed properly](http://install.python-guide.org).  Also, install the [Heroku Toolbelt](https://toolbelt.heroku.com/).

```sh
$ git clone git@github.com:heroku/python-getting-started.git
$ cd python-getting-started
$ pip install -r requirements.txt
$ python manage.py syncdb
$ foreman start web
```

Your app should now be running on [localhost:5000](http://localhost:5000/).

## Deploying to Heroku

```sh
$ heroku create
$ git push heroku master
$ heroku run python manage.py syncdb
$ heroku open
```

## Documentation

For more information about using Python on Heroku, see these Dev Center articles:

- [Python on Heroku](https://devcenter.heroku.com/categories/python)

