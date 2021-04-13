# =============================================================================
# Minet Argparse Helpers
# =============================================================================
#
# Miscellaneous helpers related to CLI argument parsing.
#
import os
import sys
from io import TextIOBase
from argparse import Action, ArgumentError
from gettext import gettext
from tqdm.contrib import DummyTqdmFile

from minet.utils import nested_get
from minet.cli.utils import (
    acquire_cross_platform_stdout,
    CsvIO
)


class SplitterType(object):
    def __init__(self, splitchar=','):
        self.splitchar = splitchar

    def __call__(self, string):
        return string.split(self.splitchar)


class BooleanAction(Action):
    """
    Custom argparse action to handle --no-* flags.
    Taken from: https://thisdataguy.com/2017/07/03/no-options-with-argparse-and-python/
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, cli_args, values, option_string=None):
        setattr(cli_args, self.dest, False if option_string.startswith('--no') else True)


class InputFileAction(Action):
    def __init__(self, option_strings, dest, dummy_csv_column=None,
                 column_dest='column', **kwargs):

        self.dummy_csv_column = dummy_csv_column
        self.column_dest = column_dest

        super().__init__(
            option_strings,
            dest,
            default=None,
            nargs='?',
            **kwargs
        )

    def __call__(self, parser, cli_args, value, option_string=None):
        if value is None:
            f = sys.stdin

            if self.dummy_csv_column is not None:

                # No stdin was piped
                if sys.stdin.isatty():
                    f = CsvIO(self.dummy_csv_column, getattr(cli_args, self.column_dest))
                    setattr(cli_args, self.column_dest, self.dummy_csv_column)
        else:
            try:
                f = open(value, 'r', encoding='utf-8')
            except OSError as e:
                args = {'filename': value, 'error': e}
                message = gettext('can\'t open \'%(filename)s\': %(error)s')
                raise ArgumentError(self, message % args)

        setattr(cli_args, self.dest, f)


class OutputFileOpener(object):
    def __init__(self, path=None):
        self.path = path

    def open(self, resume=False):
        if self.path is None:
            return DummyTqdmFile(acquire_cross_platform_stdout())

        mode = 'a' if resume else 'w'

        # As per #254: newline='' is necessary for CSV output on windows to avoid
        # outputting extra lines because of a '\r\r\n' end of line...
        return open(self.path, mode, encoding='utf-8', newline='')


class OutputFileAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(
            option_strings,
            dest,
            help='Path to the output file. By default, the results will be printed to stdout.',
            default=OutputFileOpener(),
            **kwargs
        )

    def __call__(self, parser, cli_args, value, option_string=None):
        setattr(cli_args, self.dest, OutputFileOpener(value))
        setattr(cli_args, 'output_is_file', True)


def rc_key_to_env_var(key):
    return 'MINET_%s' % '_'.join(token.upper() for token in key)


class WrappedConfigValue(object):
    def __init__(self, key, default, _type):
        self.key = key
        self.default = default
        self.type = _type

    def resolve(self, config):

        # Attempting to resolve env variable
        env_var = rc_key_to_env_var(self.key)
        env_value = os.environ.get(env_var, '').strip()

        if env_value:
            return self.type(env_value)

        return nested_get(self.key, config, self.default)


class ConfigAction(Action):
    def __init__(self, option_strings, dest, rc_key, default=None, **kwargs):
        if 'help' in kwargs:
            kwargs['help'] = kwargs['help'].rstrip('.') + '. Can also be configured in a .minetrc file as "%s" or read from the %s env variable.' % (
                '.'.join(rc_key),
                rc_key_to_env_var(rc_key)
            )

        super().__init__(
            option_strings,
            dest,
            default=WrappedConfigValue(
                rc_key,
                default,
                kwargs.get('type', str)
            ),
            **kwargs
        )

    def __call__(self, parser, cli_args, values, option_string=None):
        setattr(cli_args, self.dest, values)


def resolve_arg_dependencies(cli_args, config):
    to_close = []

    if hasattr(cli_args, 'output') and not hasattr(cli_args, 'output_is_file'):
        setattr(cli_args, 'output_is_file', False)

    for name in vars(cli_args):
        value = getattr(cli_args, name)

        # Solving wrapped config values
        if isinstance(value, WrappedConfigValue):
            setattr(cli_args, name, value.resolve(config))

        # Opening output files
        if isinstance(value, OutputFileOpener):
            value = value.open(resume=getattr(cli_args, 'resume', False))
            setattr(cli_args, name, value)

        # Finding buffers to close eventually
        if (
            isinstance(value, TextIOBase) and
            value is not sys.stdin and
            value is not sys.stdout and
            value is not sys.stderr
        ):
            to_close.append(value)

    return to_close
