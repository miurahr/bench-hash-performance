pypy performance test
=====================

Test pypy3 performance against ctypes, hashlib and memoryview combination.

Test case
---------

calculate key of 7-zip encryption which uses sha256.


Test results
------------

Mean time of each benchmark conditions.

Mean time (ms)

+---------------+-----------------+---------------------------------+
|  test logic   |   simple        |      ctypes and memoryview      |
+===============+=================+=================================+
| CPython 3.8   |   252.7252      |                  248.0225       |
+---------------+-----------------+---------------------------------+
| CPython 3.6   |   483.9979      |                  241.0997       |
+---------------+-----------------+---------------------------------+
| pypy3(head)   |   442.9166      |                  493.7977       |
+---------------+-----------------+---------------------------------+


