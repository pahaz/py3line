#!/usr/bin/env python3

# updated 2005.07.21, thanks to Jacob Oscarson
# updated 2006.03.30, thanks to Mark Eichin
# updated 2016.07.19, thanks to Pahaz Blinov

import logging
import os
import shlex
import subprocess
import sys
import re
import argparse
import types
from pprint import pprint

__version__ = '0.0.3'
NAME = 'py3line'
logger = logging.getLogger(NAME)

if sys.version_info[0] != 3:
    raise RuntimeError("Only python 3.x is supported")


def x_processor(p_index, reader, action, global_ctx):
    """
    Line based action processor
    """
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
            logger.info("processor %d: error: %r x=%r, i=%d", p_index, e, x, i)
            continue

        if result is None or result is False:
            logger.debug("processor %d: skip x=%r, i=%d", p_index, x, i)
            continue
        if result is True:
            result = x

        logger.debug("processor %d: -> %r x=%r, i=%d", p_index, result, x, i)
        yield result


def xx_processor(p_index, reader, action, global_ctx):
    """
    Stream transformation action (Stream based processor)
    """
    xx = reader
    try:
        return eval(action, global_ctx, locals())
    except TypeError as _exc:
        # fix xx[:3], xx[1:-1], ...
        if str(_exc) == "'_io.TextIOWrapper' object is not subscriptable":
            xx = list(xx)
            return eval(action, global_ctx, locals())
        raise _exc


def parseargs():
    description = (
        "Py3line is a UNIX command-line tool for line-based processing "
        "in Python with regex and output transform features "
        "similar to grep, sed, and awk."
    )

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('action',
                        metavar='action',
                        action='append', default=[],
                        help='<python_expression>')
    # parser.add_argument('files', metavar='file', nargs='*',
    #                     help='Input file  #default: stdin')

    parser.add_argument('-a', '--action',
                        metavar='action',
                        action='append', default=[],
                        help='<python_expression>')
    parser.add_argument('-p', '--pre-action',
                        metavar='pre_action',
                        action='append', default=[],
                        help='<python_expression>')

    # parser.add_argument('-o', '--out', '--output-file',
    #                     dest='output', action='store', default='-',
    #                     help="Output file  #default: '-' for stdout")
    # parser.add_argument('-i', '--in-place',
    #                     dest='is_inplace', action='store_true',
    #                     help="Output to editable file")
    # parser.add_argument('--in-place-suffix',
    #                     dest='is_inplace_suffix', action='store', default=None,
    #                     help="Output to editable file and provide a backup "
    #                          "suffix for keeping a copy of the original file")

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


def _import_modules(args, global_ctx):
    for m in args.modules:
        global_ctx[m] = __import__(m, global_ctx, global_ctx)


def _pre_actions(args, global_ctx):
    pre_actions = [compile(x.strip(), NAME, 'exec') for x in args.pre_action]
    for action in pre_actions:
        exec(action, global_ctx, global_ctx)


def _get_actions(args):
    return [compile(x.strip() or 'x', NAME, 'eval') for x in args.action]


def _get_input_output_pairs(args):
    for i, o in zip(['-'], ['-']):
        i = sys.stdin if i == '-' else open(i)
        o = sys.stdout if o == '-' else open(o, mode='w')
        yield i, o


def _process_result(writer, result):
    if result is None or result is False:
        return
    elif isinstance(result, list) or isinstance(result, tuple):
        result = ' '.join(map(str, result))
    else:
        result = str(result)
    if not result.endswith('\n'):
        result += '\n'

    writer.write(result)


def _process_results(writer, results):
    for result in results:
        if result is None or result is False or isinstance(result, Exception):
            continue
        elif isinstance(result, list) or isinstance(result, tuple):
            result = ' '.join(map(str, result))
        else:
            result = str(result)
        if not result.endswith('\n'):
            result += '\n'

        writer.write(result)


def main():
    args = parseargs()
    global_ctx = {
        'os': os,
        'sys': sys,
        're': re,
        'shlex': shlex,
        'pprint': pprint,
        'sh': lambda *x, check=True, stdout=subprocess.PIPE, shell=True, **kwargs: subprocess.run(
            *x, stdout=stdout, check=check, shell=shell,
            **kwargs).stdout.decode(),
        'spawn': lambda *x, **y: 0 == subprocess.call(
            x, stderr=subprocess.STDOUT, stdout=subprocess.DEVNULL, **y),
        'STDOUT': subprocess.STDOUT,
        'PIPE': subprocess.PIPE,
        'DEVNULL': subprocess.DEVNULL,
    }

    if args.version:
        print(__version__)
        return 0

    _setup_logger(args)
    logger.debug('arguments: %r', args)

    _import_modules(args, global_ctx)
    _pre_actions(args, global_ctx)
    actions = _get_actions(args)
    pairs = _get_input_output_pairs(args)
    index = 0
    for reader, writer in pairs:
        for action in actions:
            index += 1
            processor = x_processor if 'xx' not in action.co_names \
                else xx_processor
            reader = processor(index - 1, reader, action, global_ctx)

        results = reader
        if isinstance(results, types.GeneratorType):
            _process_results(writer, results)
        else:
            _process_result(writer, results)

    return 0


if __name__ == '__main__':
    sys.exit(main())
