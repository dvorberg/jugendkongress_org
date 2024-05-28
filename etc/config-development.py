import socket

hostname = socket.gethostname().split(".")[0]

SECRET_KEY="2FK-wi8-HLT-nhk"
SITE_URL=f"http://jugendkongress.{hostname}.tux4web.de"
WWW_PATH="/Users/diedrich/jugendkongress/www"
SKIN_PATH="/Users/diedrich/jugendkongress/skin"
DATASOURCE={ "dbname": "jugendkongress", }
