import socket

hostname = socket.gethostname().split(".")[0]

SECRET_KEY="eDc-4Zm-AU2-v07"
SITE_URL=f"http://jugendkongress.{hostname}.tux4web.de"
WWW_PATH="/Users/diedrich/jugendkongress/www"
SKIN_PATH="/Users/diedrich/jugendkongress/skin"
BRAND="jugendkongress"
DATASOURCE={ "dbname": BRAND, }
