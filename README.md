# Personal Account System (pacc)

## Setting up

The system configuration depends on environmental variables. Those can
be set by the user or in a `.env` file at the project root (here).

Those variables are:
```bash
PACS_DEBUG=1  # Can be set to anything, enters in debug mode. If not set
              # goes into production mode.
PACS_SECRET_KEY=... # SECRET_KEY in django settings
PACS_ALLOWED_HOSTS=... # comma separated ALLOWED_HOSTS for django settings
                       # e.g. 128.6.2.1,www.google.com
PACS_STATIC_ROOT=... # STATIC_ROOT for django settings.
PACS_DB_FILE=... # The path to the db file (can be relative to cur dir)
```

See .env.example for an example.
