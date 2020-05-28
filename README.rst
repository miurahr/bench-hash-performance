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


Bottlenecks
-----------

There are several bottlenecks found with profiler.
Here is an example of profiling for test_benchmark_calculate_key2()

CPython 3.8

::

      3670016    0.729    0.000    0.729    0.000 {method 'update' of '_hashlib.HASH' objects}


CPython 3.6

::
      3670016    0.842    0.000    0.842    0.000 {method 'update' of '_hashlib.HASH' objects}



PyPy3.6-7.3.x

::
     13631657    8.605    0.000   12.535    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:114(__get__)
      6815757    0.864    0.000    3.966    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:130(__set__)
      6815757    2.515    0.000    2.707    0.000 /opt/pypy3/lib_pypy/_hashlib/__init__.py:58(update)
     13631657    0.754    0.000    2.052    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:287(_subarray)
      6815913    0.439    0.000    1.797    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:343(from_param)
     13631501    0.556    0.000    1.581    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:361(_CData_output)
      6815913    0.717    0.000    1.172    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:379(__init__)
     13631657    0.902    0.000    0.902    0.000 {method 'fieldaddress' of 'StructureInstanceAutoFree' objects}
     13631501    0.527    0.000    0.527    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:393(_getvalue)
     13631501    0.341    0.000    0.498    0.000 /opt/pypy3/lib_pypy/_ctypes/basics.py:71(_CData_output)
