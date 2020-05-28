import _hashlib
import ctypes

import pytest


def calculate_key1(password: bytes, cycles: int, salt: bytes, digest: str) -> bytes:
    """Calculate 7zip AES encryption key."""
    if digest not in ('sha256'):
        raise ValueError('Unknown digest method for password protection.')
    assert cycles <= 0x3f
    if cycles == 0x3f:
        ba = bytearray(salt + password + bytes(32))
        key = bytes(ba[:32])  # type: bytes
    else:
        rounds = 1 << cycles
        m = _hashlib.new(digest)
        for round in range(rounds):
            m.update(salt + password + round.to_bytes(8, byteorder='little', signed=False))
        key = m.digest()[:32]
    return key


def calculate_key2(password: bytes, cycles: int, salt: bytes, digest: str):
    """Calculate 7zip AES encryption key.
    It utilize ctypes and memoryview buffer and zero-copy technology on Python."""
    if digest not in ('sha256'):
        raise ValueError('Unknown digest method for password protection.')
    assert cycles <= 0x3f
    if cycles == 0x3f:
        key = bytes(bytearray(salt + password + bytes(32))[:32])  # type: bytes
    else:
        rounds = 1 << cycles
        m = _hashlib.new(digest)
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


@pytest.mark.parametrize("password, cycle, salt, expected",
                         [('secret^&', 0x3f, b'i@#ri#Ildajfdk',
                           b'i@#ri#Ildajfdks\x00e\x00c\x00r\x00e\x00t\x00^\x00&\x00\x00\x00')
                          ])
def test_calculate_key1(password: str, cycle: int, salt: bytes, expected: bytes):
    key = calculate_key1(password.encode('utf-16LE'), cycle, salt, 'sha256')
    assert key == expected


@pytest.mark.parametrize("password, cycle, salt, expected",
                         [('secret^&', 0x3f, b'i@#ri#Ildajfdk',
                           b'i@#ri#Ildajfdks\x00e\x00c\x00r\x00e\x00t\x00^\x00&\x00\x00\x00')
                          ])
def test_calculate_key2(password: str, cycle: int, salt: bytes, expected: bytes):
    key = calculate_key2(password.encode('utf-16LE'), cycle, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
def test_benchmark_calculate_key1(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(calculate_key1, password, cycles, salt, 'sha256')
    assert key == expected


@pytest.mark.benchmark
def test_benchmark_calculate_key2(benchmark):
    password = 'secret'.encode('utf-16LE')
    cycles = 19
    salt = b''
    expected = b'e\x11\xf1Pz<*\x98*\xe6\xde\xf4\xf6X\x18\xedl\xf2Be\x1a\xca\x19\xd1\\\xeb\xc6\xa6z\xe2\x89\x1d'
    key = benchmark(calculate_key2, password, cycles, salt, 'sha256')
    assert key == expected

