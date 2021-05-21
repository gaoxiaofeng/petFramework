import datetime
import sys
print(sys.argv)
now = datetime.datetime.now()
print(now)
delta = datetime.timedelta(seconds=int(sys.argv[1]))
print(delta)
print(now-delta)