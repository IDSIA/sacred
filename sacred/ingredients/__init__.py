#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import sacred.optional as opt

__all__ = ['whet']

if opt.has_whetlab:
    from sacred.ingredients.whetlab import whet
else:
    whet = opt.MissingDependencyMock('whetlab')
