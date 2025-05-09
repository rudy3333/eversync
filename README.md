# Eversync – Notes, Self-Hosted Email & Calendar
![image](https://raw.githubusercontent.com/rudy3333/eversync/refs/heads/master/eversyncc/static/banner.png)

The motto of this project is secure, simple and stupid.

Eversync is a self-hosted productivity suite designed with simplicity and security at its core. It provides note-taking, calendar management, and email, all in one minimal, privacy-respecting platform.

### Run

In order to run this project, I recommend using [Gunicorn](https://gunicorn.org). In order to setup Gunicorn, please run
```
gunicorn eversync.wsgi
```

For a reverse proxy solution, I recommend either [Caddy](https://caddyserver.com) or [Nginx](https://nginx.org). 

Example instructions for running Gunicorn behind Nginx are provided [here.](https://docs.gunicorn.org/en/latest/deploy.html)
