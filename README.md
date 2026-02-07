# CTFDiddy
Downloads tasks from CTF boards and sends out notifications about important events. \
Don't ask about the name. I initially wanted to name it "ctfdd", but here we are.

## Setup
```bash
python3 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
python3 ctfdiddy.py -h
python3 ctfdiddy.py download --provider ctfd --url BASE_URL --session SESSION out/
python3 ctfdiddy.py notify --provider ctfd --notifier plyer --url BASE_URL --session SESSION --interval 0 
```

## Providers
### CTF boards
- [CTFd](https://ctfd.io/)

### Notifications
- [plyer](https://pypi.org/project/plyer/)

## Licence
This project is licenced under [Mozilla Public License Version 2.0](https://github.com/TheAirBlow/CTFDiddy/blob/main/LICENCE)