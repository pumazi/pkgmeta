# -*- coding: utf-8 -*-
import os
import sysconfig
from configparser import ConfigParser
from pkgmeta.exceptions import ConfigNotFound, ConfigReadError

__all__ = ('PkgMetaConfig', 'RepositoryConfig',
           'PKGMETA_CFGS', 'PKGMETA_CFG_LOCATIONS',)

# FIXME: Should be using packaging.resources.get_file{_path}, but these are
#        currently not working in the tests because of missing logic in
#        packaging.command.test.

_sysconfig_paths = sysconfig.get_paths()
PKG_HOME = os.path.dirname(__file__)
BASE_CONFIG = os.path.join(PKG_HOME, 'base_config')
PKGMETA_CFG_LOCATIONS = os.path.join(BASE_CONFIG, 'pkgmeta.cfg-locations')

LOCAL_CONFIG_VARS = {
    'pkgmeta_home': PKG_HOME,
    }


def _substitute_config_vars(path, local_vars=LOCAL_CONFIG_VARS):
    """Like sysconfig._subst_vars except with pkgmeta custom variables included.
    """
    config_vars = _sysconfig_paths.copy()
    sysconfig._extend_dict(config_vars, local_vars)
    path = sysconfig._subst_vars(path, config_vars)
    return path


def _retrieve_config_list(list_file):
    """Retrieve a list of configuration files that actually exist on the system
    from paths that use sysconfig variables."""
    results = []
    with open(list_file, 'r') as f:
    # Note: Tuple comprehension won't work here, because it makes a generator.
        for path in f.readlines():
            path = path.strip()
            if not path or path.startswith('#'):
                continue
            path = _substitute_config_vars(path)
            if os.path.exists(path):
                results.append(path)
    return results

# There are multiple locations where pkgmeta.cfg configs can be found.
PKGMETA_CFGS = tuple(_retrieve_config_list(PKGMETA_CFG_LOCATIONS))


class PkgMetaConfig(ConfigParser):
    """Configuration parser for pkgmeta.cfg initialization.

    This fills in any missing repository configuration and sets a
    bunch of defaults.
    """

    def __init__(self, cfg=None):
        super(PkgMetaConfig, self).__init__(allow_no_value=True)
        if cfg is None:
            cfg = PKGMETA_CFGS[0]
        self.read(cfg)
        if not hasattr(self, 'default'):
            self.default = self.sections()[0]
        self._file = cfg

    def read(self, filenames):
        """Reads configuration from a sequence."""
        if hasattr(self, '_file'):
            # This prevents anyone from loading in another config.
            raise RuntimeError("Only one config can be read in.")
        # Ensure only one file can be read in.
        if isinstance(filenames, (list, tuple)):
            filename = filenames[0]
        else:
            filename = filenames
        super(PkgMetaConfig, self).read(filename)
        # Verify the global section is in tact
        if not self.has_section('global'):
            raise ConfigReadError("[global] section missing.")
        elif not self.has_option('global', 'root'):
            raise ConfigReadError("[global] section missing a root value")
        # Read in global variables and remove the global variables section
        for name, value in self.items('global'):
            new_value = _substitute_config_vars(value)
            setattr(self, name, new_value)
        self.remove_section('global')

    def list_repositories(self):
        """List available repositories."""
        return self.sections()

    def get_repository_config(self, name=None):
        """Get a RepositoryConfig by name. If name is not given, the default or first found
        repository will be returned."""
        if name is None:
            name = self.default
        location = os.path.join(self.root, name)
        sources = [source for source in self.get(name, 'sources').split() if source] 
        return RepositoryConfig(name, location, sources)


class RepositoryConfig:

    def __init__(self, name, location, sources=[]):
        self.name = name
        self.location = location
        self.sources = sources
