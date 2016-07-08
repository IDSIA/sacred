#!/usr/bin/env python
# coding=utf-8

if __name__ == '__main__':
    import sys

    buffer = ' '
    while len(buffer):
        buffer = sys.stdin.read()
        sys.stdout.write(buffer)
        sys.stderr.write(buffer)
