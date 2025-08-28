# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import hooks as _hooks


def pre_init_check(*args, **kwargs):
    return _hooks.pre_init_check(*args, **kwargs)


def post_init_hook(*args, **kwargs):
    return _hooks.post_init_hook(*args, **kwargs)


def uninstall_hook(*args, **kwargs):
    return _hooks.uninstall_hook(*args, **kwargs)