#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.utils import iter_prefixes, join_paths


class ConfigSummary(dict):
    def __init__(self, added=(), modified=(), typechanged=(),
                 ignored_fallbacks=(), docs=()):
        super(ConfigSummary, self).__init__()
        self.added = set(added)
        self.modified = set(modified)  # TODO: test for this member
        self.typechanged = dict(typechanged)
        self.ignored_fallbacks = set(ignored_fallbacks)  # TODO: test
        self.docs = dict(docs)
        self.ensure_coherence()

    def update_from(self, config_mod, path=''):
        added = config_mod.added
        updated = config_mod.modified
        typechanged = config_mod.typechanged
        self.added &= {join_paths(path, a) for a in added}
        self.modified |= {join_paths(path, u) for u in updated}
        self.typechanged.update({join_paths(path, k): v
                                 for k, v in typechanged.items()})
        self.ensure_coherence()
        for k, v in config_mod.docs.items():
            if not self.docs.get(k, ''):
                self.docs[k] = v

    def update_add(self, config_mod, path=''):
        added = config_mod.added
        updated = config_mod.modified
        typechanged = config_mod.typechanged
        self.added |= {join_paths(path, a) for a in added}
        self.modified |= {join_paths(path, u) for u in updated}
        self.typechanged.update({join_paths(path, k): v
                                 for k, v in typechanged.items()})
        self.docs.update(config_mod.docs)
        self.ensure_coherence()

    def ensure_coherence(self):
        # make sure parent paths show up as updated appropriately
        self.modified |= {p for a in self.added for p in iter_prefixes(a)}
        self.modified |= {p for u in self.modified for p in iter_prefixes(u)}
        self.modified |= {p for t in self.typechanged
                          for p in iter_prefixes(t)}

        # make sure there is no overlap
        self.added -= set(self.typechanged.keys())
        self.modified -= set(self.typechanged.keys())
        self.modified -= self.added
