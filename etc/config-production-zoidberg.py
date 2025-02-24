import socket, os

# hostname = socket.gethostname().split(".")[0]

SECRET_KEY=os.getenv("secret_key")
SITE_URL=f"https://jugendkongress.org"
WWW_PATH="/home/people/diedrich/jugendkongress/www"
SKIN_PATH="/home/people/diedrich/jugendkongress/www/skin"
DATASOURCE={ "dbname": "jugendkongress",
             "user": "jugendkongress",
             "password": os.getenv("db_password")}
