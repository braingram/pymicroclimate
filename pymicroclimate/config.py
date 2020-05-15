import json
import os


default_fn = '~/.pymicroclimate/config.json'
default_config = {
    'data_dir': '~/.pymicroclimate/',
    'split_days': True,
    'port': '/dev/ttyACM0',
}
required_keys = ('data_dir', 'port')
key_types = (
    ('data_dir', str),
    ('port', str),
    ('split_days', bool),
)


class ConfigError(Exception):
    pass


def verify_config(cfg):
    if not isinstance(cfg, dict):
        raise ConfigError("cfg is not dict[%s]" % type(cfg))
    for k in required_keys:
        if k not in cfg:
            raise ConfigError("Missing %s" % k)
    for k, t in key_types:
        if k not in cfg:
            continue
        if not isinstance(cfg[k], t):
            raise ConfigError("%s is not %s[%s]" % (k, t, type(cfg[k])))


def load_config(fn=None):
    if fn is None:
        fn = default_fn
    cfg = default_config.copy()
    if isinstance(fn, str):
        fn = os.path.expanduser(fn)
        if os.path.exists(fn):
            with open(fn, 'r') as f:
                cfg.update(json.load(f))
    elif isinstance(fn, dict):
        cfg.update(fn)
    else:
        raise ConfigError("Invalid config: %s" % fn)
    verify_config(cfg)
    return cfg
