Improve performance of function which use hash
==============================================

Test performance against ctypes, hashlib and memoryview combination.

Test case
---------

calculate key of 7-zip encryption which uses sha256.

How to run a benchmark
----------------------

::

    $ pip install tox
    $ tox


Target logic to improve
-----------------------

Here is a simplified target function to improve performance.

::

    def calculate_key1(password: bytes, cycles: int, salt: bytes):
        rounds = 1 << cycles
        m = _hashlib.new('sha256')
        for round in range(rounds):
            m.update(salt + password + round.to_bytes(8, byteorder='little', signed=False))
        key = m.digest()[:32]
        return key


Understandings of target logic
------------------------------

Effect of 'cycles'
^^^^^^^^^^^^^^^^

We can easily understand that a round of 'for loop' is easily very huge as a number of 2^cycles.
There is 19 in benchmark condition, that lead loops and calls m.update() with 2^19 times
which is equals to 524288.


Bytes operations
^^^^^^^^^^^^^^^

There are several built-in data type 'bytes' operations. First, we see a fact that
it concatenates bytes variable 'salt' and 'password' again and again.
Next, we become aware that 'Hash.update(val)' may copy val into C's 'uchar * buf' then
call OpenSSL's library function.


Zero-Copy hack
--------------

OK then we can try reducing these memory manipulation operations.
You can find an article about zero-copy operation titled
[High-Performance in Python with Zero-Copy and the Buffer protocol](https://julien.danjou.info/high-performance-in-python-with-zero-copy-and-the-buffer-protocol/)
by JULIEN DANJOU.

He introduce 'memoryview' which provide C-language level buffer handling without memory copy.
I have an idea to utilize memoryview and ctypes Structure subclass to construct structure and
pass its raw memory direct to Hash.update().

Here is an improved function that utilize memoryview

Here is a ctypes structure definition.

::

        class RoundBuf(ctypes.LittleEndianStructure):
            _pack_ = 1
            _fields_ = [
                ('saltpassword', ctypes.c_ubyte * length),
                ('round', ctypes.c_uint64)
            ]

A size of field 'saltpassword' is a dyamic, because 'password' will be given by user with variable length.
so 'length' is not a constant.
So by using dynamic feature of python, I defined a calculate_key function as follows.

::

    def calculate_key2(password, cycles, salt):
        rounds = 1 << cycles
        m = _hashlib.new('sha256')
        length = len(salt) + len(password)

        class RoundBuf(ctypes.LittleEndianStructure):
            _pack_ = 1
            _fields_ = [
                ('saltpassword', ctypes.c_ubyte * length),
                ('round', ctypes.c_uint64)
            ]

        buf = RoundBuf()
        for i, c in enumerate(salt + password):
            buf.saltpassword[i] = c
        buf.round = 0
        mv = memoryview(buf)  # type: ignore # noqa
        while buf.round < rounds:
            m.update(mv)
            buf.round += 1
        key = m.digest()[:32]
        return key


Profiling a code
----------------

There are several bottlenecks found with profiler.
Here is an example of profiling for test_benchmark_calculate_key2()

CPython 3.8

::

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    3670016    0.729    0.000    0.729    0.000 {method 'update' of '_hashlib.HASH' objects}


CPython 3.6

::

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    3670016    0.842    0.000    0.842    0.000 {method 'update' of '_hashlib.HASH' objects}



PyPy3.6-7.3.2-alpha

::

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    13631657    8.605    0.000   12.535    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:114(__get__)
    6815757     0.864    0.000    3.966    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:130(__set__)
    6815757     2.515    0.000    2.707    0.000 /opt/pypy3/lib_pypy/_hashlib/__init__.py:58(update)
    13631657    0.754    0.000    2.052    0.000 /opt/pypy3/lib_pypy/_ctypes/structure.py:287(_subarray)
    6815913     0.439    0.000    1.797    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:343(from_param)
    13631501    0.556    0.000    1.581    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:361(_CData_output)
    6815913     0.717    0.000    1.172    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:379(__init__)
    13631657    0.902    0.000    0.902    0.000 {method 'fieldaddress' of 'StructureInstanceAutoFree' objects}
    13631501    0.527    0.000    0.527    0.000 /opt/pypy3/lib_pypy/_ctypes/primitive.py:393(_getvalue)
    13631501    0.341    0.000    0.498    0.000 /opt/pypy3/lib_pypy/_ctypes/basics.py:71(_CData_output)


In CPython platform, we can successfully remove an overhead of memory copy and dominant bottleneck is
a Hash.update() function, which is a C implementation.
Otherwise, on pypy3 (which should be a snapshot as in May 27, 2020 because of ctypes bug fixed),
There are bottle necks around 'ctypes' in pypy over hashlib.Hash function.

It is because pypy uses CFFI for C-language interface other than Ctypes, so pypy implenent it in (R)Python.


Another way?
------------

When taking benchmark with first simple logics on pypy3, we can find a fact that
we can advice to Hash.update() to use raw memory.

Here is a result of calculate_key1() on pypy3.

::

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    7864335    2.581    0.000    5.242    0.000 /opt/pypy3/lib_pypy/_hashlib/__init__.py:58(update)
    7864350    2.531    0.000    2.531    0.000 {method 'from_buffer' of 'CompiledFFI' objects}
    7864320    1.325    0.000    1.325    0.000 {method 'to_bytes' of 'int' objects}


Here is a code block of _hashlib/__init__.py: update()

::

    def update(self, string):
        buf = ffi.from_buffer(string)
        with self.lock:
            # XXX try to not release the GIL for small requests
            lib.EVP_DigestUpdate(self.ctx, buf, len(buf))

If we can reduce an overhead of 'from_buffer()' it may help improving performance.

Let's modify a first code;

::

    -            m.update(salt + password + round.to_bytes(8, byteorder='little', signed=False))
    +            m.update(memoryview(salt + password + round.to_bytes(8, byteorder='little', signed=False)))

Then we can see a result improve a performance on pypy3.

::

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    8388624    2.505    0.000    3.593    0.000 /opt/pypy3/lib_pypy/_hashlib/__init__.py:58(update)
    8388608    0.992    0.000    0.992    0.000 {method 'to_bytes' of 'int' objects}
    8388640    0.952    0.000    0.952    0.000 {method 'from_buffer' of 'CompiledFFI' objects}


What is a first large number of profiling?
------------------------------------------

A first number of profiling result, 'ncalls', is a number of calls of a specified function.
When reducing a ncalls, it can perform a better result in total.

Here is another approach; concatenate values first then pass it to Hash.update() in batch.

Here is an updated target function:

::

    def calculate_key3(password, cycles, salt):
        concat = 1 << 6
        rounds = 1 << cycles
        m = _hashlib.new('sha256')
        saltpassword = salt + password
        round = 0
        while round < rounds:
            val = bytearray()
            for _ in range(concat):
                val += saltpassword + round.to_bytes(8, byteorder='little', signed=False)
                round += 1
            m.update(val)
        key = m.digest()[:32]
        return key

In this example, reduce a loop number to 2^(cycles-6) times and construct an input bytes value
by looping 2^6 times which will be produce 2048 bytes of data when byte length of password is 12.

When pypy, we can also add 'memoryview' to 'm.update(val)', becomes 'm.update(memoryview(val))'


The last example can be rewritten with list comprehension expression and 'b''.join()' for
bytes concatenation.

The latest resulted code(simplified) is

::

    def calculate_key3(password, cycles, salt):
        rounds = 1 << 6
        stages = 1 << (cycles - 6)  # Hash.update() calls 'stages' times
        m = _hashlib.new('sha256')
        saltpassword = salt + password
        s = 0  # 's' is as 'stage * rounds' then '(s + i)' is as same as a 'round' in the original code.
        for stage in range(stages):
            m.update(memoryview(b''.join([saltpassword + (s + i).to_bytes(8, byteorder='little', signed=False) for i in range(rounds)])))
            s += rounds
        key = m.digest()[:32]
        return key



Test results
------------

In many conditions, last case archives a fastest result.
Mean time (ms) of each benchmark conditions.

+---------------+------------+------------------------+-------------------------+
|  test logic   | simple     | ctypes and memoryview  | concat bytes and update |
+===============+============+========================+=========================+
| CPython 3.8   | 364.6985   |         233.1391       |            **215.7877** |
+---------------+------------+------------------------+-------------------------+
| CPython 3.7   | 414.0788   |         309.5720       |            **239.9061** |
+---------------+------------+------------------------+-------------------------+
| CPython 3.6   | 603.3538   |         **239.4337**   |               447.3005  |
+---------------+------------+------------------------+-------------------------+
| pypy3(head)   | 236.5434   |         676.8878       |            **115.7619** |
+---------------+------------+------------------------+-------------------------+
