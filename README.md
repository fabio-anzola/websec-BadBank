# websec-BadBank

# Angabe
- Create a vulnerable/extremely secure web application
- Write a 2-5 page documentation about your web project

# Unser Projekt
Wir haben uns entschieden, unser Projekt unsecure, aber sinnvoll zu coden. 
Unser Projekt soll eine REST API für Banking sein.

## Ideen für unsecure Ideen
- Login Token besteht nur aus username+unix Zeitstempel auf die Minute genau
- Im Transfer-money Endpunkt kann Sender und reciever angegeben werden ohne dass gecheckt wird ob der Sender der richtige ist solange ein valider login token für irgendeinen Account vorliegt
- Es können Negative beträge überwiesen werden (daher ich ziehe Geld vom Empfänger ab)
- Wenn man genaug ausgibt (-> "Kredit"), kommt es zu einem underflow und der Kontostand wird zu Integer.Max
- ...
