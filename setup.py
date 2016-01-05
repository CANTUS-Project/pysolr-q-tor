try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name="pysolr-tornado",
    version="3.3.3a1",
    description="Lightweight python wrapper for Apache Solr. Based on 'pysolr' but with Tornado!",
    author='Christopher Antila',
    author_email='christopher@antila.ca',
    long_description=open('README.rst', 'r').read(),
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    url='https://github.com/CANTUS-Project/pysolr-tornado/',
    license='BSD',
    install_requires=[
        'tornado>=4.0'
    ],
    extras_require={
        'tomcat': [
            'lxml>=3.0',
            'cssselect',
        ],
    }
)
