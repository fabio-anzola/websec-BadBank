# websec-BadBank

# Angabe
- Create a vulnerable/extremely secure web application
- Write a 2-5 page documentation about your web project

# Unser Projekt
Wir haben uns entschieden, unser Projekt unsecure, aber sinnvoll zu coden. 
Unser Projekt soll eine REST API für Banking sein.

## Ansätze für insecurites
- Login Token besteht nur aus username+unix Zeitstempel auf die Minute genau
- Im Transfer-money Endpunkt kann Sender und reciever angegeben werden ohne dass gecheckt wird ob der Sender der richtige ist solange ein valider login token für irgendeinen Account vorliegt
- Es können Negative beträge überwiesen werden (daher ich ziehe Geld vom Empfänger ab)
- Wenn man genaug ausgibt (-> "Kredit"), kommt es zu einem underflow und der Kontostand wird zu Integer.Max
- sitemap / robots file mit allen endpoints
- ...


# Techstack
- Python mit FastAPI
- Postgresql
- Docker


# Endpoints
## /login
POST /login

IN: {"username": "","password": ""}
OUT: {"token": "<username>:<unix-minute>"}

Insecurties:
- Weak Token
- Kein MFA
- Passwörter werden nicht gehasht
- Login Request wird mit Parametern gelogged
- Kein rate limiting

## /register
POST /register

## /account/{id}
GET /account/{id}

OUT: {"IBAN": "", "kontostand": <cent>, "owner": ""}

## /transfer
POST /transfer

IN: { "from": "<IBAN>", "to": "<IBAN>", "amount": <cent> }

## /credit/request
POST /admin/request

## /credit/{id}/approve
POST /credit/{id}/approve

## /credit/{id}/deny
POST /credit/{id}/deny

