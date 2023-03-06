#!../venv/bin/python
from app import memcachePool

memcachePool.run('0.0.0.0',5002,debug=False)


