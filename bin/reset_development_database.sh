#!/bin/bash
set -x
dumpsql=$HOME/jugendkongress/sql/current_dump.sql

ssh zoidberg pg_dump jugendkongress > $dumpsql

dropdb jugendkongress
createdb -T template0 -l de_DE.UTF-8 jugendkongress

psql -1 -f $dumpsql jugendkongress

