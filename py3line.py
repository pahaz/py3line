#!/usr/bin/env python3

# updated 2005.07.21, thanks to Jacob Oscarson
# updated 2006.03.30, thanks to Mark Eichin
# updated 2016.07.19, thanks to Pahaz Blinov

import logging
import os
import subprocess
import sys
import re
import argparse

__version__ = '0.0.1'
NAME = 'py3line'
logger = logging.getLogger(NAME)
global_ctx = {
    'sh': lambda *x: subprocess.check_output(x).decode(),
    'spawn': lambda *x: 0 == subprocess.call(
        x, stderr=subprocess.STDOUT, stdout=subprocess.DEVNULL),
}


def parseargs():
    description = (
        "Pyline is a UNIX command-line tool for line-based processing "
        "in Python with regex and output transform features "
        "similar to grep, sed, and awk."
    )

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('action',
                        metavar='action',
                        action='append', default=[],
                        help='<python_expression>')
    parser.add_argument('files', metavar='file', nargs='*',
                        help='Input file  #default: stdin')

    parser.add_argument('-a', '--action',
                        metavar='action',
                        action='append', default=[],
                        help='<python_expression>')

    parser.add_argument('-o', '--out', '--output-file',
                        dest='output', action='store', default='-',
                        help="Output file  #default: '-' for stdout")
    parser.add_argument('-i', '--in-place',
                        dest='is_inplace', action='store_true',
                        help="Output to editable file")
    parser.add_argument('--in-place-suffix',
                        dest='is_inplace_suffix', action='store', default=None,
                        help="Output to editable file and provide a backup "
                             "suffix for keeping a copy of the original file")

    parser.add_argument('-m', '--modules',
                        dest='modules',
                        action='append',
                        default=[],
                        help='for m in modules: import m  #default: []')

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true')
    parser.add_argument('-q', '--quiet',
                        dest='quiet',
                        action='store_true')

    parser.add_argument('--version',
                        dest='version',
                        action='store_true',
                        help='Print the version string')

    return parser.parse_args()


def x_processor(p_index, reader, action, global_ctx):
    for i, x in enumerate(reader):
        if isinstance(x, str) and x.endswith('\n'):
            x = x[:-1]

        # * if the result of any linewise expression is a boolean or None,
        #   it acts as a filter for that line (like grep)
        # * if the result of any linewise expression is a callable object,
        #   it will be passed the current value as the new value of line.
        try:
            result = eval(action, global_ctx, locals())
        except Exception as e:
            result = e

        if result is None or result is False:
            logger.debug("processor %d: skip x=%r, i=%d", p_index, x, i)
            continue
        if result is True:
            result = x

        logger.debug("processor %d: -> %r x=%r, i=%d", p_index, result, x, i)
        yield result


def _get_actions(args):
    return [compile(action.strip() or 'x', NAME, 'eval')
            for action in args.action]


def _setup_logger(args):
    if not logger.handlers:  # if no handlers, add a new one (console)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(levelname)-8s| %(message)s')
        )
        logger.addHandler(console_handler)

    if not args.quiet:
        logger.setLevel(logging.WARN)
        if args.verbose:
            logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.ERROR)

    # capture_warnings
    logging.captureWarnings(True)
    pywarnings = logging.getLogger('py.warnings')
    pywarnings.handlers.extend(logger.handlers)


def _make_input_output_pairs(args):
    for i, o in zip(['-'], ['-']):
        i = sys.stdin if i == '-' else open(i)
        o = sys.stdout if o == '-' else open(o, mode='w')
        yield i, o


def main():
    args = parseargs()

    if args.version:
        print(__version__)
        return 0

    _setup_logger(args)
    logger.debug('arguments: %r', args)

    actions = _get_actions(args)
    pairs = _make_input_output_pairs(args)
    index = 0
    for reader, writer in pairs:
        for action in actions:
            index += 1
            reader = x_processor(index - 1, reader, action, global_ctx)
        for result in reader:
            if result is None or result is False:
                continue
            elif isinstance(result, list) or isinstance(result, tuple):
                result = ' '.join(map(str, result))
            else:
                result = str(result)
            if not result.endswith('\n'):
                result += '\n'

            writer.write(result)

    return 0


if __name__ == '__main__':
    sys.exit(main())
