
from pricing_pipeline import run_pricing_pipeline_us # type: ignore

def main():
    items = [
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 1
    {"desc": "blind flange", "size": '1" x 1"'},              # 2
    {"desc": "instrument tee", "size": '6" x 1"'},            # 3
    {"desc": "spool", "size": '6" x 10\'-2 5/16"'},           # 4
    {"desc": "spool", "size": '6" x 1\'-7 7/16"'},            # 5
    {"desc": "spool", "size": '6" x 1\'-4 11/16"'},           # 6
    {"desc": "spool", "size": '6" x 2\''},                    # 7
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 8
    {"desc": "blind flange", "size": '1" x 1"'},              # 9
    {"desc": "instrument tee", "size": '6" x 1"'},            # 10
    {"desc": "spool", "size": '6" x 0\'- 11 7/8"'},           # 11
    {"desc": "spool", "size": '6" x 1\'-5 7/16"'},            # 12
    {"desc": "spool", "size": '6" x 3\'-2 7/8"'},             # 13
    {"desc": "spool", "size": '6" x 10\'-7 9/16"'},           # 14
    {"desc": "spool", "size": '6" x 11\'-1 1/8"'},            # 15
    {"desc": "spool", "size": '6" x 19\'-11 3/8"'},           # 16
    {"desc": "spool", "size": '6" x 20\''},                   # 17
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 18
    {"desc": "spool", "size": '6" x 20\''},                   # 19
    {"desc": "spool", "size": '6" x 3\'-3 7/8"'},             # 20
    {"desc": "spool", "size": '6" x 1\'-4"'},                 # 21
    {"desc": "spool", "size": '6" x 3\'-5 5/16"'},            # 22
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 23
    {"desc": "spool", "size": '6" x 20\''},                   # 24
    {"desc": "spool", "size": '6" x 1\'-8 1/4"'},             # 25
    {"desc": "spool", "size": '6" x 11\'-3 5/8"'},            # 26
    {"desc": "spool", "size": '6" x 19\'-11 7/8"'},           # 27
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 28
    {"desc": "45 elbow", "size": '6" x 6"'},                  # 29
    {"desc": "spool", "size": '6" x 20\''},                   # 30
    {"desc": "spool", "size": '6" x 6"'},                     # 31
    {"desc": "spool", "size": '6" x 5\'-10 3/4"'},            # 32
    {"desc": "spool", "size": '6" x 3\'-9 1/16"'},            # 33
    {"desc": "spool", "size": '6" x 2\'-7 5/8"'},             # 34
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 35
    {"desc": "spool", "size": '6" x 2\'-7 3/8"'},             # 36
    {"desc": "spool", "size": '6" x 19\'-10 1/2"'},           # 37
    {"desc": "spool", "size": '6" x 15\''},                   # 38
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 39
    {"desc": "spool", "size": '6" x 10\'-10"'},               # 40
    {"desc": "spool", "size": '6" x 14\'-11 7/8"'},           # 41
    {"desc": "spool", "size": '6" x 6\'-11 7/8"'},            # 42
    {"desc": "90 elbow", "size": '6" x 6"'},                  # 43
    {"desc": "blind flange", "size": '1" x 1"'},              # 44
    {"desc": "reducing tee", "size": '8" x 6"'},              # 45
    {"desc": "instrument tee", "size": '6" x 1"'},            # 46
    {"desc": "spool", "size": '6" x 19\'-9 7/8"'},            # 47
    {"desc": "spool", "size": '6" x 8\' 3/16"'},                # 48
    ]  # your items list
    
    df = run_pricing_pipeline_us(items)
    print(df)

if __name__ == "__main__":
    main()



