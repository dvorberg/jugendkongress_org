import pathlib

from juko import plastic_bottle
from juko.db import execute

def main():
    cursor = execute("SELECT no FROM room")

    for (no,) in cursor.fetchall():
        p = pathlib.Path(f"{no}.jpg")
        print(no, p.exists())

main()
