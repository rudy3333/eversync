# Eversync – Notes, Office Suite & Calendar

![Banner](https://raw.githubusercontent.com/rudy3333/eversync/refs/heads/master/eversyncc/static/banner.png)

<p align="center">
  <b>Secure, Simple, and Stupid</b><br>
  <i>All-in-one productivity suite</i>
</p>


## ✨ Features

- 📝 Note-taking with rich text support
- 📅 Calendar & event management
- 📂 Document storage and management
- 🗂️ Office suite utilities
- 🔒 Privacy-first, self-hosted
- 🔔 Notifications & reminders
- 🖼️ Whiteboard for visual collaboration
- 🔗 Embeds and web archives
- 🎵 Pomodoro timer, music, and more

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rudy3333/eversync.git
   cd eversync
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```
4. **Start the development server:**
   ```bash
   python manage.py runserver
   ```


## ⚙️ Environment Variables

Create a `.env` file in your project root with the following variables:

```
SECRET_KEY=your-django-secret-key
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=your_db_port
RECAPTCHA_PUBLIC_KEY=your_recaptcha_public_key
RECAPTCHA_PRIVATE_KEY=your_recaptcha_private_key
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=webmaster@localhost
```

- For push notifications, place your Firebase service account JSON as `fcm_secret.json` in the project root.
- For reCAPTCHA, get your keys from [Google reCAPTCHA](https://www.google.com/recaptcha/admin).


## Deployment

### Gunicorn (Recommended)

To run with Gunicorn:
```bash
gunicorn eversync.wsgi
```

### Docker

A `Dockerfile` is included for containerized deployment:
```bash
docker build -t eversync .
docker run -d -p 8000:8000 eversync
```

### Reverse Proxy

For production, use a reverse proxy like [Caddy](https://caddyserver.com) or [Nginx](https://nginx.org). See [Gunicorn deployment docs](https://docs.gunicorn.org/en/latest/deploy.html) for example configurations.

## 🤝 Contributing

Contributions are welcome! To get started:
- Fork this repository
- Create a new branch (`git checkout -b feature/your-feature`)
- Commit your changes
- Open a pull request

Please see the [issues](https://github.com/rudy3333/eversync/issues) page for ideas and discussion.

## 📬 Support & Contact

- For questions, open an [issue](https://github.com/rudy3333/eversync/issues)
- For direct contact, reach out via [GitHub profile](https://github.com/rudy3333)

## 📄 License

This project is licensed under our custom [license](https://github.com/rudy3333/eversync/blob/master/LICENSE) — do whatever you want, I probably won't care.