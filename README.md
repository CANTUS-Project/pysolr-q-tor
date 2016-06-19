pysolr-tornado
==============

``pysolr-tornado`` is a Python library providing access to [Apache Solr](https://lucene.apache.org/solr/)
via Tornado coroutines.

[![Build Status](https://img.shields.io/travis/CANTUS-Project/pysolr-tornado/master.svg?style=flat-square)](https://travis-ci.org/CANTUS-Project/pysolr-tornado)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/d86805093f4747f4b32207852afaa375)](https://www.codacy.com/app/christopher/pysolr-tornado)

This project is a fork of `pysolr`, hosted on GitHub at https://github.com/toastdriven/pysolr. We
offer a few minor improvements over `pysolr`, but we attempt to keep the APIs identical. However,
it is impossible to offer a compatible API because Tornado coroutines are coroutines, and must
therefore be used with Python's `yield` keyword.

If you are trying to decide between `pysolr` and `pysolr-tornado`, we recommend `pysolr` unless you
are already sure that you want to use Tornado.

**NOTE**: Although this library is called "pysolr-tornado," this is an illegal module name in Python
so you must import the library as ``import pysolrtornado``.

**NOTE**: The upstream `extract()` functionality is not (yet) working here. If this is important for
you, please file an issue, and we will try to work on it.


Features
--------

* Basic operations such as selecting, updating, and deleting.
* Index optimization.
* `"More Like This" <http://wiki.apache.org/solr/MoreLikeThis>`_ support (if set up in Solr).
* `Spelling correction <http://wiki.apache.org/solr/SpellCheckComponent>`_ (if set up in Solr).
* Timeout support.


Requirements
------------

`pysolr-tornado` works with and requires:

* Solr 4 or 5
* CPython 3
* Tornado 4

The exact versions of software with which `pysolr-tornado` is tested changes over time. Please refer
to our page on [Travis-CI](https://travis-ci.org/CANTUS-Project/pysolr-tornado) to determine whether
the Python and Solr versions you use are already tested. As of January 2016, these are CPython 3.3,
3.4, and 3.5; and Solr 4.10.4, 5.3.1, and 5.4.0.

The upstream `pysolr` project still supports CPython 2.6 and 2.7. The code may work with Python 2,
but we no longer test with Python 2 due to a lack of interest.


Basic Use Example
-----------------

```python
import pysolrtornado

# Setup a Solr instance. The timeout is optional.
solr = pysolrtornado.Solr('http://localhost:8983/solr/', timeout=10)

# How you'd index data.
yield solr.add([
    {
        "id": "doc_1",
        "title": "A test document",
    },
    {
        "id": "doc_2",
        "title": "The Banana: Tasty or Dangerous?",
    },
])

# Later, searching is easy. In the simple case, just a plain Lucene-style
# query is fine.
results = yield solr.search('bananas')

# The ``Results`` object stores total results found, by default the top
# ten most relevant results and any additional data like
# facets/highlighting/spelling/etc.
print("Saw {0} result(s).".format(len(results)))

# Just loop over it to access the results.
for result in results:
    print("The title is '{0}'.".format(result['title']))

# For a more advanced query, say involving highlighting, you can pass
# additional options to Solr.
results = yield solr.search('bananas', **{
    'hl': 'true',
    'hl.fragsize': 10,
})

# You can also perform More Like This searches, if your Solr is configured
# correctly.
similar = yield solr.more_like_this(q='id:doc_2', mltfl='text')

# Finally, you can delete either individual documents...
yield solr.delete(id='doc_1')

# ...or all documents.
yield solr.delete(q='*:*')
```


LICENSE
-------

``pysolr-tornado`` is licensed under the New BSD license.


Running Tests
-------------

The ``run-tests.py`` script will automatically perform the steps below and is recommended for testing by
default unless you need more control.

**Running a test Solr instance**

Download, configuration, and starting the test Solr server is handled automatically by the
`start-solr-test-server.sh` script. If you wish to run this script yourself, you must set the
`SOLR_VERSION` environment variable, like this:

    $ SOLR_VERSION="4.10.4" ./start-solr-test-server.sh

**Running the tests**

Python 3::

    python3 -m unittest tests
