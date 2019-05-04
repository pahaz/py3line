**Author**: `Pahaz White`_

**Repo**: https://github.com/pahaz/py3line/

Pyline is a UNIX command-line tool for bash one-liner scripts.
It's python line alternative to `grep`, `sed`, and `awk`.

This project inspired by: `piep`_, `pysed`_, `pyline`_, `pyp`_ and
`Jacob+Mark recipe <https://code.activestate.com/recipes/437932-pyline-a-grep-like-sed-like-command-line-tool/>`_

**WHY I MAKE IT?**

Sometimes, I have to use `sed` / `awk` / `grep`. Usually for simple text
processing. Find some pattern inside the text file using Python regexp,
or comment/uncomment some config line by bash one line command.

I always forget the necessary options and `sed` / `awk` DSL.
But I now python, I like it, and I want use it for this simple bash tasks.
Default `python -c` is not enough to write readable bash one-liners.

Why not a `pyline`?
 * Don`t support python3
 * Have many options
 * Don`t support command chaining

**PRINCIPLES**

 * AS MUCH SIMPLE TO UNDERSTAND BASH ONE LINER SCRIPT AS POSSIBLE
 * AS MUCH EASY TO INSTALL AS POSSIBLE
 * AS MUCH SMALL CODEBASE AS POSSIBLE

Installation
============

`py3line`_ is on PyPI, so simply run:

::

    pip install py3line

or ::

    sudo curl -L "https://43-63976011-gh.circle-artifacts.com/0/py3line-$(uname -s)-$(uname -m)" -o /usr/local/bin/py3line
    sudo chmod +x /usr/local/bin/py3line

to have it installed in your environment.

For installing from source, clone the
`repo <https://github.com/pahaz/py3line>`_ and run::

    python setup.py install

Tutorial
========

Lets start with examples, we want to evaluate a number of words in each line:

.. code-block:: bash

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split(); len(x)"
    2
    1
    3


Py3line produces a transform over the input data stream.
Py3line transform is constructed from a sequence of python actions.

 * **echo -e "Here are\nsome\nwords for you."** -- create an input data stream consists of three lines
 * **|** -- pipeline input data stream to py3line
 * **"x.split(); len(x)"** -- define two py3line actions: "x.split()" and "len(x)". Each of them transform an input stream step by step.

The example above can be represented as the following python pseudo-code::

    import sys

    for x in sys.stdin.readlines():

        # 1) action "x.split()"
        x = x.split()

        # 2) action "len(x)"
        x = len(x)

        print(x)


Stream stransform
-----------------

Lets try more complex example, we want to evaluate a sum of number of words in each line ::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split(); len(x); sum(stream)"
    6


Here we have stream transformation action **"sum(stream)"**.

It can be represented as python pseudo-code::

    import sys

    stream = []

    for x in sys.stdin.readlines():

        # 1) action "x.split()"
        x = x.split()

        # 2) action "len(x)"
        x = len(x)

        stream.append(x)

    # 3) action "sum(stream)"
    print(sum(stream))


Details
=======

Let us define some terminology. **py3line "action1; action2; action3**

We have actions: action1, action2 and action3.
Each of them may be element based or stream based.

Element based and stream based actions
--------------------------------------

**Element based** action can be represented as python pseudo-code::

    stream = ...
    new_stream = []

    for x in stream:
        # DO ELEMENT BASED ACTION ON `x`
        result = eval(compile(action_x, ..., 'eval'), {'x': x})
        new_stream.append(result)

    stream = new_stream

**Stream based** action can be represented as python pseudo-code::

    stream = ...

    # DO STREAM BASED ACTION ON `stream`
    stream = eval(compile(action_stream, ..., 'eval'), {'stream': stream})

Pre-actions
-----------

Sometimes you want prepare some variables or import some modules.

You can use **-m** options for import module::

    ./py3line.py -m shlex "shlex.split(x)[13]"

You also exec some pre actions before stream processed::

    ./py3line.py "rgx = re.compile(r' is ([A-Z]\w*)'); rgx.search(x).group(1)"


Statement actions ??
--------------------

Sometimes you want define some variable during stream processing.

You can exec some statment actions before each stream element processed::

    ./py3line.py "z = 7; int(x); z += 0 if x < 0 else x; z else stream"


Some others examples
====================

.. code-block:: bash

    # Print every line (null transform)
    $ cat ./testsuit/test.txt | ./py3line.py
    This is my cat,
     whose name is Betty.
    This is my dog,
     whose name is Frank.
    This is my fish,
     whose name is George.
    This is my goat,
     whose name is Adam.

Or the same: ``cat ./testsuit/test.txt | ./py3line.py x`` and 
``cat ./testsuit/test.txt | ./py3line.py stream``.

.. code-block:: bash

    # Number every line
    $ cat ./testsuit/test.txt | ./py3line.py "enumerate(stream)"
    0 This is my cat,
    1  whose name is Betty.
    2 This is my dog,
    3  whose name is Frank.
    4 This is my fish,
    5  whose name is George.
    6 This is my goat,
    7  whose name is Adam.

.. code-block:: bash

    # Print every first and last word
    $ cat ./testsuit/test.txt | ./py3line.py "x.split()[0], x.split()[-1]"
    This cat,
    whose Betty.
    This dog,
    whose Frank.
    This fish,
    whose George.
    This goat,
    whose Adam.

Or just: ``cat ./testsuit/test.txt | ./py3line.py "x.split(); x[0], x[-1]"``

.. code-block:: bash

    # Split into words and print (strip al non word char like comma, dot, etc)
    $ cat ./testsuit/test.txt | ./py3line.py "re.findall(r'\w+', x)"
    This is my cat
    whose name is Betty
    This is my dog
    whose name is Frank
    This is my fish
    whose name is George
    This is my goat
    whose name is Adam

.. code-block:: bash

    # Regex matching with groups
    $ cat ./testsuit/test.txt | ./py3line.py "re.findall(r' is ([A-Z]\w*)', x) or skip"
    Betty
    Frank
    George
    Adam

.. code-block:: bash

    # cat ./testsuit/test.txt | ./py3line.py "re.search(r' is ([A-Z]\w*)', x) or skip; x.group(1)"
    $ cat ./testsuit/test.txt | ./py3line.py "rgx = re.compile(r' is ([A-Z]\w*)'); rgx.search(x) or skip; x.group(1)"
    Betty
    Frank
    George
    Adam

.. code-block:: bash

    ## Original Examples
    # Print out the first 20 characters of every line
    # cat ./testsuit/test.txt | ./py3line.py "enumerate(stream); x[1] if x[0] < 2 else skip;"
    $ cat ./testsuit/test.txt | ./py3line.py "list(stream)[:2]"
    This is my cat,
     whose name is Betty.

.. code-block:: bash

    # Print just the URLs in the access log
    $ cat ./testsuit/nginx.log | ./py3line.py -m shlex "shlex.split(x)[13]"
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    GET /admin/moktoring/session/add/ HTTP/1.1
    GET /admin/jsi18n/ HTTP/1.1
    GET /static/admin/img/icon-calendar.svg HTTP/1.1
    GET /static/admin/img/icon-clock.svg HTTP/1.1
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    GET /logout/?reason=startApplication HTTP/1.1
    GET / HTTP/1.1
    GET /login/?next=/ HTTP/1.1
    POST /admin/customauth/user/?q=%D0%9F%D0%B0%D1%81%D0%B5%D1%87%D0%BD%D0%B8%D0%BA HTTP/1.1

.. code-block:: bash

    # Print most common accessed urls and filter accessed more then 5 times
    $ cat ./testsuit/nginx.log | ./py3line.py -m shlex -m collections "shlex.split(x)[13]; collections.Counter(stream).most_common(); x[0] if x[1] > 5 else skip"
    HEAD / HTTP/1.0

Examples
--------

    # create directory tree
    echo -e "y1\nx2\nz3" | py3line -m pathlib "pathlib.Path('/DATA/' + x +'/db-backup/').mkdir(parents=True, exist_ok=True)"

    group by 3 lines ... (https://askubuntu.com/questions/1052622/separate-log-text-according-to-paragraph)

HELP
----

::

    usage: py3line.py [-h] [-a action] [-p pre_action] [-o OUTPUT] [-i]
                      [--in-place-suffix IS_INPLACE_SUFFIX] [-m MODULES] [-v] [-q]
                      [--version]
                      action [file [file ...]]

    Py3line is a UNIX command-line tool for line-based processing in Python with
    regex and output transform features similar to grep, sed, and awk.

    positional arguments:
      action                <python_expression>
      file                  Input file #default: stdin

    optional arguments:
      -h, --help            show this help message and exit
      -a action, --action action
                            <python_expression>
      -p pre_action, --pre-action pre_action
                            <python_expression>
      -o OUTPUT, --out OUTPUT, --output-file OUTPUT
                            Output file #default: '-' for stdout
      -i, --in-place        Output to editable file
      --in-place-suffix IS_INPLACE_SUFFIX
                            Output to editable file and provide a backup suffix
                            for keeping a copy of the original file
      -m MODULES, --modules MODULES
                            for m in modules: import m #default: []
      -v, --verbose
      -q, --quiet
      --version             Print the version string


.. _Pahaz White: https://github.com/pahaz/
.. _py3line: https://pypi.python.org/pypi/py3line/
.. _pyp: https://pypi.python.org/pypi/pyp/
.. _piep: https://github.com/timbertson/piep/tree/master/piep/
.. _pysed: https://github.com/dslackw/pysed/blob/master/pysed/main.py
.. _pyline: https://github.com/westurner/pyline/blob/master/pyline/pyline.py
.. _pyfil: https://github.com/ninjaaron/pyfil