#!/bin/bash

##  Copyright 2024 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved.
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##
##  I have added a copy of the GPL in the file LICENSE


hostname=$(hostname -s)

if [[ hostname == zoidberg ]]
then
    HOME=/home/web/jugendkongress
fi

cd $HOME/jugendkongress
. $HOME/jugendkongress/virtualenv/bin/activate

export FLASK_ENV=development
export FLASK_APP=juko.app_factory:create_app

export YOURAPPLICATION_SETTINGS=$HOME/jugendkongress/etc/config-development.py

export DEBUG_SQL=true
flask run -p 5001 --debug

