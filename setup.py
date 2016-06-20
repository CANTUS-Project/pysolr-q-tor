try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


LONG_DESCRIPTION = '''
``pysolr-tornado`` is a Python library providing access to [Apache Solr](https://lucene.apache.org/solr/)
via Tornado coroutines.

.. image:: https://img.shields.io/travis/CANTUS-Project/pysolr-tornado/master.svg?style=flat-square
    :target: https://travis-ci.org/CANTUS-Project/pysolr-tornado
    :alt: Build Status
.. image:: https://www.quantifiedcode.com/api/v1/project/e650bacf59a0427fa3388771f34a7df4/badge.svg
    :target: https://www.quantifiedcode.com/app/project/e650bacf59a0427fa3388771f34a7df4
    :alt: Code Issues

This project is a fork of `pysolr`, hosted on GitHub at https://github.com/toastdriven/pysolr. We
offer a few minor improvements over `pysolr`, but we attempt to keep the APIs identical. However,
it is impossible to offer a compatible API because Tornado coroutines are coroutines, and must
therefore be used with Python's `yield` keyword.

If you are trying to decide between `pysolr` and `pysolr-tornado`, we recommend `pysolr` unless you
are already sure that you want to use Tornado.

Versions
--------

With ``pysolr-tornado`` 4.0, the version numbers no longer correspond meaningfully to upstream
versions. We made the decision to jump to a new major release because of the refactoring of the
:class:`Results` class, which we view as backward incompatible. We sympathize with the upstream's
decision to release this as a point release, because it is such a minor change in most situations,
but it broke our client application and it may break yours too.
'''


setup(
    name='pysolr-tornado',
    version='4.0.1',
    description='A library to access Solr via Tornado coroutines.',
    author='Daniel Lindsley, Joseph Kocherhans, Jacob Kaplan-Moss, Christopher Antila',
    author_email='christopher@antila.ca',
    long_description=LONG_DESCRIPTION,
    py_modules=[
        'pysolrtornado'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    url='https://github.com/CANTUS-Project/pysolr-tornado/',
    license='BSD',
    install_requires=[
        'tornado>=4.0,<5'
    ],
    extras_require={
        'tomcat': [
            'lxml>=3.0',
            'cssselect',
        ],
    }
)
