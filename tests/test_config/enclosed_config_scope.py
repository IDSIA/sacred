#!/usr/bin/env python
# coding=utf-8


from sacred.config.config_scope import ConfigScope

SIX = 6


@ConfigScope
def cfg():
    answer = 7 * SIX


@ConfigScope
def cfg2():
    answer = 6 * SEVEN
