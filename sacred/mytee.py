import ctypes

libc = ctypes.CDLL(None)
buffer = ctypes.create_string_buffer(64)

l = 1
while l:
    l = libc.read(0, buffer, 64)
    libc.write(1, buffer, l)
    libc.write(2, buffer, l)



