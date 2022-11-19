# Tootroll
Tootroll is a Python package to read timelines from the Mastodon network.

## Prerequisites
### Python
Python 3.7 or higher is required to run this package.

### Mastodon account (optional)
To read public timelines an account is not needed.

A Mastodon account is required to read the Home timeline.
To setup a Mastodon account, visit: [joinmastodon.org](https://joinmastodon.org/).

To acquire a (private) API key ("access token"):
1. go to "edit profile"
2. click "<> Development"
3. click "New application"
Application name can be anything. Leave the Redirect URI unchanged. Because we only want to read timelines, we recommend to only check "read" for Scopes. Write and follow is not needed.
4. click "Submit" and open the link to the created Application
5. Copy the "access token" (Client key and secret are not needed)

## Install
The package can be installed from PyPI:
```
python -m pip install tootroll
```

## Quick setup
### Configure public (default) profile
When installed for the first time, API keys must be configured.
To allow easy switching between servers, public/ private APIs the package allows to define multiple named profiles.

To setup the default profile, run the following command and follow instructions.
Pick a server from the list or set your own (hostname of Mastodon server).
For the default profile, we recommend to say (N)o when asked for private API key.
```
python -m tootroll --configure
```
Test if it works by getting timeline data for 1 toot.
```
python -m tootroll --pub --limit 1
```
Pipe through a JSON parser
```
python -m tootroll --pub --limit 5 |python -m json.tool

```

### Configure private profile
```
python -m tootroll --configure --profile myProfile
```
When asked to use private API, type (Y)es.
Copy the access token from your Mastodon account.

All configuration files are stored under ~/.tootroll.

```
python -m tootroll --home --profile myProfile --limit 5 |python -m json.tool
```

## Usage
```
python -m tootroll --help
```
```
usage: tootroll [-h] [--pub | --home | --tags TAGS | --configure | --show [profiles]] [--profile PROFILE] [-l LIMIT]

options:
  -h, --help            show this help message and exit
  --pub                 Show public timeline of server
  --home                Show home timeline
  --tags TAGS           Tag(s). Use comma-separated string to pass a list
  --configure           Create or update a profile
  --show [profiles]     Show configuration (e.g. list of profiles)
  --profile PROFILE     Select a profile to use. If left empty, lists configured profiles
  -l LIMIT, --limit LIMIT
                        Limit number of toots. Defaults to 10
```
