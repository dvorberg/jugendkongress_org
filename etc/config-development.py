import socket, os

hostname = socket.gethostname().split(".")[0]

SECRET_KEY=os.getenv("secret_key")

if hostname == "leela":
    SITE_URL=f"http://juko.{hostname}.tux4web.de"
    WWW_PATH="/Users/diedrich/jugendkongress/www"
    SKIN_PATH="/Users/diedrich/jugendkongress/www/skin"
    DATASOURCE={ "dbname": "jugendkongress", }
elif hostname == "zoidberg":
    SITE_URL=f"http://debug.jugendkongress.org"
    WWW_PATH="/home/people/diedrich/jugendkongress/www"
    SKIN_PATH="/home/people/diedrich/jugendkongress/www/skin"
    DATASOURCE={ "dbname": "jugendkongress",
                 "user": "jugendkongress",
                 "password": os.getenv("db_password")}
