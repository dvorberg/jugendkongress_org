import re, sys

section_re = re.compile(r"# (.*?) \((\d+)\)")
def main():
    section = None
    section_sum = None
    current_sum = 0

    for line in sys.stdin.readlines():
        if line.strip() == "": continue

        match = section_re.match(line)
        if match is not None:
            if section is not None:
                if current_sum != section_sum:
                    print(section, "doesn’t match", file=sys.stderr)
                    sys.exit(1)

            section = match.group(1)
            section_sum = int(match.group(2))
            current_sum = 0
        else:
            no, beds = line.strip().split(" ")
            beds = int(beds)

            current_sum += beds

            print(f"INSERT INTO room (no, beds, section) "
                  f"VALUES ('{no}', {beds}, '{section}');")


main()
