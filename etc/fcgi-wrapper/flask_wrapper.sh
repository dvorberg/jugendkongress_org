#!/bin/bash

hostname=$(hostname -s)

if [[ "$hostname" == "leela" ]]
then
    project_root=/Users/diedrich/jugendkongress
    export HOME=/Users/diedrich
    export PATH=$PATH:/opt/local/bin
    export FLASK_ENV=development
    export YOURAPPLICATION_SETTINGS=$project_root/etc/config-development.py
else
    project_root=/home/web/jugendkongress
    export FLASK_ENV=production
    export YOURAPPLICATION_SETTINGS=$project_root/etc/config-production-$hostname.py
fi

. $project_root/virtualenv/bin/activate

#$project_root/virtualenv/bin/python -c "from juko.app_factory import create_app"

exec $project_root/virtualenv/bin/python \
     $project_root/etc/fcgi-wrapper/flask_fcgi.py

