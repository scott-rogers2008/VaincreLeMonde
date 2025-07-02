### Create python environment

```bash
python -m venv .venv
source .venv/bin/activate

pip install django djangorestframework djangorestframework-jwt pwJWT pytz certifi
```

### Create backend

```bash
django-admin startproject backend .
python manage.py startapp API
```

### Create frontend

```bash
ng new frontend
```

