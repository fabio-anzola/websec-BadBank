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
- Request wird mit Parametern gelogged
- Kein rate limiting
- default user admin:admin

## /register
POST /register

IN: {"username": "","password": "", "vorname": "", "nachname": "", "gebDatum": "", "email": "", "svNummer": ""}

Insecurties:
- passwort als cleartext gespeichert
- keine passwort regeln
- SQL Injection möglich
- Request wird mit Parametern gelogged

## /account/{iban}
GET /account/{id}

OUT: {"IBAN": "", "kontostand": <cent>, "owner": ""}

Insecurties:
- jeder kann jedes Konto ansehen

## /transfer
POST /transfer

IN: { "from": "<IBAN>", "to": "<IBAN>", "amount": <cent> }

Insecurties:
- From und To feld kann frei angegeben werden
- Amount kann negativ sein (abbuchung von empfänger)
- Amount ist nicht gegen over/underflow geschützt

## /credit/request
POST /admin/request

IN: { "kunde": "", "amount": <cent>, "laufzeit": <monate> }

## /credit/{id}/approve
POST /credit/{id}/approve

Insecurties:
- Endpoint kann auch von nicht-admins aufgerufen werden

## /credit/{id}/deny
POST /credit/{id}/deny

Insecurties:
- Datenbank Eintrag bleibt bestehen (späterer approve möglich)

## /robots.txt
GET /robots.txt

## /sitemap.xml
GET /sitemap.xml

## /debug
GET /debug

## /logs
GET /logs