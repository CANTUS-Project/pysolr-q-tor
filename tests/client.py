# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import subprocess
import sys

from tornado import httpclient, testing

from pysolrtornado import (Solr, Results, SolrError, unescape_html, safe_urlencode,
                           force_unicode, force_bytes, sanitize, json, ET, IS_PY3,
                           clean_xml_string)

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from urllib.parse import unquote_plus
except ImportError:
    from urllib import unquote_plus

if IS_PY3:
    from io import StringIO
else:
    from StringIO import StringIO


class UtilsTestCase(unittest.TestCase):
    def test_unescape_html(self):
        self.assertEqual(unescape_html('Hello &#149; world'), 'Hello \x95 world')
        self.assertEqual(unescape_html('Hello &#x64; world'), 'Hello d world')
        self.assertEqual(unescape_html('Hello &amp; ☃'), 'Hello & ☃')
        self.assertEqual(unescape_html('Hello &doesnotexist; world'), 'Hello &doesnotexist; world')

    def test_safe_urlencode(self):
        self.assertEqual(force_unicode(unquote_plus(safe_urlencode({'test': 'Hello ☃! Helllo world!'}))), 'test=Hello ☃! Helllo world!')
        self.assertEqual(force_unicode(unquote_plus(safe_urlencode({'test': ['Hello ☃!', 'Helllo world!']}, True))), "test=Hello \u2603!&test=Helllo world!")
        self.assertEqual(force_unicode(unquote_plus(safe_urlencode({'test': ('Hello ☃!', 'Helllo world!')}, True))), "test=Hello \u2603!&test=Helllo world!")

    def test_sanitize(self):
        self.assertEqual(sanitize('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19h\x1ae\x1bl\x1cl\x1do\x1e\x1f'), 'hello'),

    def test_force_unicode(self):
        self.assertEqual(force_unicode(b'Hello \xe2\x98\x83'), 'Hello ☃')
        # Don't mangle, it's already Unicode.
        self.assertEqual(force_unicode('Hello ☃'), 'Hello ☃')

        self.assertEqual(force_unicode(1), '1', "force_unicode() should convert ints")
        self.assertEqual(force_unicode(1.0), '1.0', "force_unicode() should convert floats")
        self.assertEqual(force_unicode(None), 'None', 'force_unicode() should convert None')

    def test_force_bytes(self):
        self.assertEqual(force_bytes('Hello ☃'), b'Hello \xe2\x98\x83')
        # Don't mangle, it's already a bytestring.
        self.assertEqual(force_bytes(b'Hello \xe2\x98\x83'), b'Hello \xe2\x98\x83')

    def test_clean_xml_string(self):
        self.assertEqual(clean_xml_string('\x00\x0b\x0d\uffff'), '\x0d')


class ResultsTestCase(unittest.TestCase):
    def test_init(self):
        default_results = Results([{'id': 1}, {'id': 2}], 2)
        self.assertEqual(default_results.docs, [{'id': 1}, {'id': 2}])
        self.assertEqual(default_results.hits, 2)
        self.assertEqual(default_results.highlighting, {})
        self.assertEqual(default_results.facets, {})
        self.assertEqual(default_results.spellcheck, {})
        self.assertEqual(default_results.stats, {})
        self.assertEqual(default_results.qtime, None)
        self.assertEqual(default_results.debug, {})
        self.assertEqual(default_results.grouped, {})

        full_results = Results(
            docs=[{'id': 1}, {'id': 2}, {'id': 3}],
            hits=3,
            # Fake data just to check assignments.
            highlighting='hi',
            facets='fa',
            spellcheck='sp',
            stats='st',
            qtime='0.001',
            debug=True,
            grouped=['a']
        )
        self.assertEqual(full_results.docs, [{'id': 1}, {'id': 2}, {'id': 3}])
        self.assertEqual(full_results.hits, 3)
        self.assertEqual(full_results.highlighting, 'hi')
        self.assertEqual(full_results.facets, 'fa')
        self.assertEqual(full_results.spellcheck, 'sp')
        self.assertEqual(full_results.stats, 'st')
        self.assertEqual(full_results.qtime, '0.001')
        self.assertEqual(full_results.debug, True)
        self.assertEqual(full_results.grouped, ['a'])

    def test_len(self):
        small_results = Results([{'id': 1}, {'id': 2}], 2)
        self.assertEqual(len(small_results), 2)

        wrong_hits_results = Results([{'id': 1}, {'id': 2}, {'id': 3}], 7)
        self.assertEqual(len(wrong_hits_results), 3)

    def test_iter(self):
        long_results = Results([{'id': 1}, {'id': 2}, {'id': 3}], 3)

        to_iter = list(long_results)
        self.assertEqual(to_iter[0], {'id': 1})
        self.assertEqual(to_iter[1], {'id': 2})
        self.assertEqual(to_iter[2], {'id': 3})


class SolrTestCase(testing.AsyncTestCase):
    def setUp(self):
        super(SolrTestCase, self).setUp()
        self.server_url = 'http://localhost:8983/solr/core0'
        self.timeout = 30  # DEBUG
        self.solr = Solr(self.server_url, timeout=self.timeout, ioloop=self.io_loop)
        self.docs = [
            {
                'id': 'doc_1',
                'title': 'Example doc 1',
                'price': 12.59,
                'popularity': 10,
            },
            {
                'id': 'doc_2',
                'title': 'Another example ☃ doc 2',
                'price': 13.69,
                'popularity': 7,
            },
            {
                'id': 'doc_3',
                'title': 'Another thing',
                'price': 2.35,
                'popularity': 8,
            },
            {
                'id': 'doc_4',
                'title': 'doc rock',
                'price': 99.99,
                'popularity': 10,
            },
            {
                'id': 'doc_5',
                'title': 'Boring',
                'price': 1.12,
                'popularity': 2,
            },
        ]

        # Clear it.
        # NB: this must be synchronous or else "post.sh" might be called before the delete command
        #     is run, or worse, the delete command could be run during a test.
        if self.clear_solr() != 200:
            self.fail('Could not clear Solr before the test.')

        # Index our docs.
        try:
            # TODO: make a direct Solr request
            subprocess.check_call(['tests/post.sh', 'tests/test_data.xml'], stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as cpe:
            self.fail(cpe)

    def clear_solr(self):
        "Clear the test Solr instance by deleting all its records. Synchronous method."
        synchttp = httpclient.HTTPClient()
        delete_body = force_bytes('<delete><query>*:*</query></delete>')
        headers = {'Content-type': 'text/xml; charset=utf-8'}
        return synchttp.fetch('{}/update?commit=true'.format(self.server_url),
                              method='POST',
                              body=delete_body,
                              headers=headers,
                              request_timeout=self.timeout).code

    def test_init(self):
        default_solr = Solr(self.server_url)
        self.assertEqual(default_solr.url, self.server_url)
        self.assertTrue(isinstance(default_solr.decoder, json.JSONDecoder))
        self.assertEqual(default_solr.timeout, 60)

        self.assertEqual(self.solr.url, self.server_url)
        self.assertTrue(isinstance(self.solr.decoder, json.JSONDecoder))
        self.assertEqual(self.solr.timeout, self.timeout)
        self.assertIs(self.solr._ioloop, self.io_loop)

    def test__create_full_url(self):
        # Nada.
        self.assertEqual(self.solr._create_full_url(path=''), 'http://localhost:8983/solr/core0')
        # Basic path.
        self.assertEqual(self.solr._create_full_url(path='pysolr_tests'), 'http://localhost:8983/solr/core0/pysolr_tests')
        # Leading slash (& making sure we don't touch the trailing slash).
        self.assertEqual(self.solr._create_full_url(path='/pysolr_tests/select/?whatever=/'), 'http://localhost:8983/solr/core0/pysolr_tests/select/?whatever=/')

    @testing.gen_test
    def test__send_request_1(self):
        "Test a valid request."
        resp_body = yield self.solr._send_request('GET', 'select/?q=doc&wt=json')
        self.assertTrue('"numFound":3' in resp_body)

    @testing.gen_test()#timeout=480)
    def test__send_request_2(self):
        "Test a lowercase method & a body."
        resp_body = yield self.solr._send_request('GET', 'select/?q=doc&wt=json')
        self.assertTrue('"numFound":3' in resp_body)

        xml_body = '<add><doc><field name="id">doc_12</field><field name="title">what is up doc?</field></doc></add>'
        resp_body = yield self.solr._send_request('POST', 'update/?softCommit=true', body=xml_body, headers={
            'Content-type': 'text/xml; charset=utf-8',
        })
        self.assertTrue('<int name="status">0</int>' in resp_body)

        resp_body = yield self.solr._send_request('GET', 'select/?q=doc&wt=json')
        self.assertTrue('"numFound":4' in resp_body)

    @testing.gen_test
    def test__send_request_3(self):
        "Test protocol-less server URL (ValueError)."
        self.solr.url = 'solrcom.org'
        try:
            yield self.solr._send_request('get', 'select/?q=doc&wt=json')
        except SolrError as sol_err:
            self.assertTrue(sol_err.args[0].startswith(Solr._FETCH_VALUE_ERROR[:20]))

    @testing.gen_test
    def test__send_request_4(self):
        "Test too-long server URL (UnicodeError)."
        # TODO: why does this always come out as ValueError-ish?
        self.solr.url = 'http://thisistheverylongpathtomysolrtestserverbutitwillnotworkeventhoughthatmakesmesad.org'
        try:
            yield self.solr._send_request('get', 'select/?q=doc&wt=json')
        except SolrError as sol_err:
            self.assertTrue(sol_err.args[0].startswith(Solr._FETCH_UNICODE_ERROR[:15]))

    @testing.gen_test
    def test__send_request_5(self):
        "Test unresolveable DNS server URL (gaierror)."
        self.solr.url = 'http://yeoldesolrserver.music'
        try:
            yield self.solr._send_request('get', 'select/?q=doc&wt=json')
        except SolrError as sol_err:
            self.assertTrue(sol_err.args[0].startswith(Solr._FETCH_SOCKET_ERROR[:20]))

    @testing.gen_test
    def test__send_request_6(self):
        "Test unknown HTTP method (KeyError)."
        try:
            yield self.solr._send_request('dance', 'select/?q=doc&wt=json')
        except SolrError as sol_err:
            self.assertTrue(sol_err.args[0].startswith(Solr._FETCH_KEY_ERROR[:20]))

    @testing.gen_test
    def test__send_request_7(self):
        "Test connection error (ConnectionRefusedError, subclass of ConnectionError)."
        # we'll roll our own mock for this test
        def mock_fetch(*args, **kwargs):
            raise ConnectionRefusedError('whatever')
        self.solr._client.fetch = mock_fetch
        try:
            yield self.solr._send_request('get', 'intersect/')
        except SolrError as sol_err:
            self.assertTrue(sol_err.args[0].startswith(Solr._FETCH_CONN_ERROR[:20]))

    @testing.gen_test
    def test__send_request_8(self):
        "Test 404 from Server (HTTPError)."
        try:
            yield self.solr._send_request('get', 'intersect/')
        except SolrError as sol_err:
            self.assertEqual(sol_err.args[0], '404: Not Found')

    @testing.gen_test
    def test__select(self):
        # Short params.
        resp_body = yield self.solr._select({'q': 'doc'})
        resp_data = json.loads(resp_body)
        self.assertEqual(resp_data['response']['numFound'], 3)

        # Long params.
        resp_body = yield self.solr._select({'q': 'doc' * 1024})
        resp_data = json.loads(resp_body)
        self.assertEqual(resp_data['response']['numFound'], 0)
        self.assertEqual(len(resp_data['responseHeader']['params']['q']), 3 * 1024)

    @testing.gen_test
    def test__mlt(self):
        resp_body = yield self.solr._mlt({'q': 'id:doc_1', 'mlt.fl': 'title'})
        resp_data = json.loads(resp_body)
        self.assertEqual(resp_data['response']['numFound'], 0)

    @testing.gen_test
    def test__suggest_terms(self):
        resp_body = yield self.solr._select({'terms.fl': 'title'})
        resp_data = json.loads(resp_body)
        self.assertEqual(resp_data['response']['numFound'], 0)

    @testing.gen_test
    def test__update_1(self):
        xml_body = '<add><doc><field name="id">doc_12</field><field name="title">Whee!</field></doc></add>'
        resp_body = yield self.solr._update(xml_body)
        self.assertTrue('<int name="status">0</int>' in resp_body)

        results = yield self.solr.search('title:Whee!')
        self.assertEqual(len(results), 1)

    @testing.gen_test
    def test__update_2(self):
        "_soft_commit() with softCommit=True"
        xml_body = '<add><doc><field name="id">doc_12</field><field name="title">Whee!</field></doc></add>'
        resp_body = yield self.solr._update(xml_body, softCommit=True)
        self.assertTrue('<int name="status">0</int>' in resp_body)

        results = yield self.solr.search('title:Whee!')
        self.assertEqual(len(results), 1)

    def test__extract_error_1(self):
        resp = httpclient.HTTPResponse(httpclient.HTTPRequest('http://cantusdatabase.org/'),
                                       500,
                                       reason='Someone Spilled Soup on the Server')
        self.assertEqual(self.solr._extract_error(resp), "[Reason: Someone Spilled Soup on the Server]")

    def test__extract_error_2(self):
        resp = httpclient.HTTPResponse(httpclient.HTTPRequest('http://cantusdatabase.org/'),
                                       500)
        self.assertEqual(self.solr._extract_error(resp), "[Reason: Internal Server Error]")

    def test__scrape_response(self):
        # Jetty.
        resp_1 = self.solr._scrape_response({'server': 'jetty'}, '<html><body><pre>Something is broke.</pre></body></html>')
        self.assertEqual(resp_1, ('Something is broke.', u''))

        # Other.
        resp_2 = self.solr._scrape_response({'server': 'crapzilla'}, '<html><head><title>Wow. Seriously weird.</title></head><body><pre>Something is broke.</pre></body></html>')
        self.assertEqual(resp_2, ('Wow. Seriously weird.', u''))

    @unittest.skipIf(sys.version_info < (2, 7), reason=u'Python 2.6 lacks the ElementTree 1.3 interface required for Solr XML error message parsing')
    def test__scrape_response_coyote_xml(self):
        resp_3 = self.solr._scrape_response({'server': 'coyote'}, '<?xml version="1.0"?>\n<response>\n<lst name="responseHeader"><int name="status">400</int><int name="QTime">0</int></lst><lst name="error"><str name="msg">Invalid Date String:\'2015-03-23 10:43:33\'</str><int name="code">400</int></lst>\n</response>\n')
        self.assertEqual(resp_3, ("Invalid Date String:'2015-03-23 10:43:33'", "Invalid Date String:'2015-03-23 10:43:33'"))

        # Valid XML with a traceback
        resp_4 = self.solr._scrape_response({'server': 'coyote'}, """<?xml version="1.0"?>
<response>
<lst name="responseHeader"><int name="status">500</int><int name="QTime">138</int></lst><lst name="error"><str name="msg">Internal Server Error</str><str name="trace">org.apache.solr.common.SolrException: Internal Server Error at java.lang.Thread.run(Thread.java:745)</str><int name="code">500</int></lst>
</response>""")
        self.assertEqual(resp_4, (u"Internal Server Error", u"org.apache.solr.common.SolrException: Internal Server Error at java.lang.Thread.run(Thread.java:745)"))

    def test__scrape_response_tomcat(self):
        """Tests for Tomcat error responses"""

        resp_0 = self.solr._scrape_response({'server': 'coyote'}, '<html><body><h1>Something broke!</h1><pre>gigantic stack trace</pre></body></html>')
        self.assertEqual(resp_0, ('Something broke!', ''))

        # Invalid XML
        bogus_xml = '<?xml version="1.0"?>\n<response>\n<lst name="responseHeader"><int name="status">400</int><int name="QTime">0</int></lst><lst name="error"><str name="msg">Invalid Date String:\'2015-03-23 10:43:33\'</str><int name="code">400</int></lst>'
        reason, full_html = self.solr._scrape_response({'server': 'coyote'}, bogus_xml)
        self.assertEqual(reason, None)
        self.assertEqual(full_html, bogus_xml.replace("\n", ""))


    def test__from_python(self):
        self.assertEqual(self.solr._from_python(datetime.date(2013, 1, 18)), '2013-01-18T00:00:00Z')
        self.assertEqual(self.solr._from_python(datetime.datetime(2013, 1, 18, 0, 30, 28)), '2013-01-18T00:30:28Z')
        self.assertEqual(self.solr._from_python(True), 'true')
        self.assertEqual(self.solr._from_python(False), 'false')
        self.assertEqual(self.solr._from_python(1), '1')
        self.assertEqual(self.solr._from_python(1.2), '1.2')
        self.assertEqual(self.solr._from_python(b'hello'), 'hello')
        self.assertEqual(self.solr._from_python('hello ☃'), 'hello ☃')
        self.assertEqual(self.solr._from_python('\x01test\x02'), 'test')

    def test__to_python(self):
        self.assertEqual(self.solr._to_python('2013-01-18T00:00:00Z'), datetime.datetime(2013, 1, 18))
        self.assertEqual(self.solr._to_python('2013-01-18T00:30:28Z'), datetime.datetime(2013, 1, 18, 0, 30, 28))
        self.assertEqual(self.solr._to_python('true'), True)
        self.assertEqual(self.solr._to_python('false'), False)
        self.assertEqual(self.solr._to_python(1), 1)
        self.assertEqual(self.solr._to_python(1.2), 1.2)
        self.assertEqual(self.solr._to_python(b'hello'), 'hello')
        self.assertEqual(self.solr._to_python('hello ☃'), 'hello ☃')
        self.assertEqual(self.solr._to_python(['foo', 'bar']), 'foo')
        self.assertEqual(self.solr._to_python(('foo', 'bar')), 'foo')
        self.assertEqual(self.solr._to_python('tuple("foo", "bar")'), 'tuple("foo", "bar")')

    def test__is_null_value(self):
        self.assertTrue(self.solr._is_null_value(None))
        self.assertTrue(self.solr._is_null_value(''))

        self.assertFalse(self.solr._is_null_value('Hello'))
        self.assertFalse(self.solr._is_null_value(1))

    @testing.gen_test
    def test_search_1(self):
        "Basic searches"
        results = yield self.solr.search('doc')
        self.assertEqual(len(results), 3)

        results = yield self.solr.search('example')
        self.assertEqual(len(results), 2)

        results = yield self.solr.search('nothing')
        self.assertEqual(len(results), 0)

    @testing.gen_test
    def test_search_2(self):
        "Advanced search"
        results = yield self.solr.search('doc', **{
            'debug': 'true',
            'hl': 'true',
            'hl.fragsize': 8,
            'facet': 'on',
            'facet.field': 'popularity',
            'spellcheck': 'true',
            'spellcheck.collate': 'true',
            'spellcheck.count': 1,
            # TODO: Can't get these working in my test setup.
            # 'group': 'true',
            # 'group.field': 'id',
        })
        self.assertEqual(len(results), 3)
        self.assertTrue('explain' in results.debug)
        self.assertEqual(results.highlighting, {u'doc_4': {}, u'doc_2': {}, u'doc_1': {}})
        self.assertEqual(results.spellcheck, {})
        self.assertEqual(results.facets['facet_fields']['popularity'], ['10', 2, '7', 1, '2', 0, '8', 0])
        self.assertTrue(results.qtime is not None)
        # TODO: Can't get these working in my test setup.
        # self.assertEqual(results.grouped, '')

    @testing.gen_test
    def test_more_like_this(self):
        results = yield self.solr.more_like_this('id:doc_1', 'text')
        self.assertEqual(len(results), 0)

    @testing.gen_test
    def test_suggest_terms(self):
        results = yield self.solr.suggest_terms('title', '')
        self.assertEqual(len(results), 1)
        self.assertEqual(results, {'title': [('doc', 3), ('another', 2), ('example', 2), ('1', 1), ('2', 1), ('boring', 1), ('rock', 1), ('thing', 1)]})

    def test__build_doc(self):
        doc = {
            'id': 'doc_1',
            'title': 'Example doc ☃ 1',
            'price': 12.59,
            'popularity': 10,
        }
        doc_xml = force_unicode(ET.tostring(self.solr._build_doc(doc), encoding='utf-8'))
        self.assertTrue('<field name="title">Example doc ☃ 1</field>' in doc_xml)
        self.assertTrue('<field name="id">doc_1</field>' in doc_xml)
        self.assertEqual(len(doc_xml), 152)

    @testing.gen_test
    def test_add_1(self):
        "Test without boost"
        res_doc = yield self.solr.search('doc')
        res_exa = yield self.solr.search('example')

        self.assertEqual(len(res_doc), 3)
        self.assertEqual(len(res_exa), 2)

        yield self.solr.add([
            {
                'id': 'doc_6',
                'title': 'Newly added doc',
            },
            {
                'id': 'doc_7',
                'title': 'Another example doc',
            },
        ])

        res_doc = yield self.solr.search('doc')
        res_exa = yield self.solr.search('example')

        self.assertEqual(len(res_doc), 5)  # there are 2 instead of 5
        self.assertEqual(len(res_exa), 3)  # there are 1 instead of 3

    @testing.gen_test
    def test_add_2(self):
        "Test add with boost"
        self.assertEqual(len((yield self.solr.search('doc'))), 3)  # there are 5 instead of 3

        yield self.solr.add([{'id': 'doc_6', 'title': 'Important doc'}],
                            boost={'title': 10.0})

        yield self.solr.add([{'id': 'doc_7', 'title': 'Spam doc doc'}],
                            boost={'title': 0})

        res = yield self.solr.search('doc')
        self.assertEqual(len(res), 5)  # there are 2 instead of 5
        self.assertEqual('doc_6', res.docs[0]['id'])  # this passes

    @testing.gen_test
    def test_field_update(self):
        originalDocs = yield self.solr.search('doc')
        self.assertEqual(len(originalDocs), 3)
        updateList = []
        for i, doc in enumerate(originalDocs):
            updateList.append( {'id': doc['id'], 'popularity': 5} )
        yield self.solr.add(updateList, fieldUpdates={'popularity': 'inc'})

        updatedDocs = yield self.solr.search('doc')
        self.assertEqual(len(updatedDocs), 3)
        for i, (originalDoc, updatedDoc) in enumerate(zip(originalDocs, updatedDocs)):
            self.assertEqual(len(updatedDoc.keys()), len(originalDoc.keys()))
            self.assertEqual(updatedDoc['popularity'], originalDoc['popularity'] + 5)
            self.assertEqual(True, all(updatedDoc[k] == originalDoc[k] for k in updatedDoc.keys() if not k in ['_version_', 'popularity']))

        yield self.solr.add([
            {
                'id': 'multivalued_1',
                'title': 'Multivalued doc 1',
                'word_ss': ['alpha', 'beta'],
            },
            {
                'id': 'multivalued_2',
                'title': 'Multivalued doc 2',
                'word_ss': ['charlie', 'delta'],
            },
        ])

        originalDocs = yield self.solr.search('multivalued')
        self.assertEqual(len(originalDocs), 2)
        updateList = []
        for i, doc in enumerate(originalDocs):
            updateList.append( {'id': doc['id'], 'word_ss': ['epsilon', 'gamma']} )
        yield self.solr.add(updateList, fieldUpdates={'word_ss': 'add'})

        updatedDocs = yield self.solr.search('multivalued')
        self.assertEqual(len(updatedDocs), 2)
        for i, (originalDoc, updatedDoc) in enumerate(zip(originalDocs, updatedDocs)):
            self.assertEqual(len(updatedDoc.keys()), len(originalDoc.keys()))
            self.assertEqual(updatedDoc['word_ss'], originalDoc['word_ss'] + ['epsilon', 'gamma'])
            self.assertEqual(True, all(updatedDoc[k] == originalDoc[k] for k in updatedDoc.keys() if not k in ['_version_', 'word_ss']))

    @testing.gen_test
    def test_delete(self):
        self.assertEqual(len((yield self.solr.search('doc'))), 3)
        yield self.solr.delete(id='doc_1')
        self.assertEqual(len((yield self.solr.search('doc'))), 2)
        yield self.solr.delete(q='price:[0 TO 15]')
        self.assertEqual(len((yield self.solr.search('doc'))), 1)

        self.assertEqual(len((yield self.solr.search('*:*'))), 1)
        yield self.solr.delete(q='*:*')
        self.assertEqual(len((yield self.solr.search('*:*'))), 0)

        # TODO: figure out how to make these errors work
        # Need at least one.
        #self.assertRaises(ValueError, self.solr.delete)
        # Can't have both.
        #self.assertRaises(ValueError, self.solr.delete, id='foo', q='bar')

    @testing.gen_test
    def test_commit(self):
        self.assertEqual(len((yield self.solr.search('doc'))), 3)
        yield self.solr.add([
            {
                'id': 'doc_6',
                'title': 'Newly added doc',
            }
        ], commit=False)
        self.assertEqual(len((yield self.solr.search('doc'))), 3)
        yield self.solr.commit()
        self.assertEqual(len((yield self.solr.search('doc'))), 4)

    @testing.gen_test
    def test_optimize(self):
        # Make sure it doesn't blow up. Side effects are hard to measure. :/
        self.assertEqual(len((yield self.solr.search('doc'))), 3)
        yield self.solr.add([
            {
                'id': 'doc_6',
                'title': 'Newly added doc',
            }
        ], commit=False)
        self.assertEqual(len((yield self.solr.search('doc'))), 3)
        yield self.solr.optimize()
        self.assertEqual(len((yield self.solr.search('doc'))), 4)

    def test_extract(self):
        "This method is not implemented with Tornado yet."
        self.assertRaises(NotImplementedError, self.solr.extract, 'whatever')

    #def test_extract(self):
        #fake_f = StringIO("""
            #<html>
                #<head>
                    #<meta charset="utf-8">
                    #<meta name="haystack-test" content="test 1234">
                    #<title>Test Title ☃&#x2603;</title>
                #</head>
                    #<body>foobar</body>
            #</html>
        #""")
        #fake_f.name = "test.html"
        #extracted = self.solr.extract(fake_f)

        ## Verify documented response structure:
        #self.assertIn('contents', extracted)
        #self.assertIn('metadata', extracted)

        #self.assertIn('foobar', extracted['contents'])

        #m = extracted['metadata']

        #self.assertEqual([fake_f.name], m['stream_name'])

        #self.assertIn('haystack-test', m, "HTML metadata should have been extracted!")
        #self.assertEqual(['test 1234'], m['haystack-test'])

        ## Note the underhanded use of a double snowman to verify both that Tika
        ## correctly decoded entities and that our UTF-8 characters survived the
        ## round-trip:
        #self.assertEqual(['Test Title ☃☃'], m['title'])

    def test_full_url(self):
        self.solr.url = 'http://localhost:8983/solr/core0'
        full_url = self.solr._create_full_url(path='/update')

        # Make sure trailing and leading slashes do not collide:
        self.assertEqual(full_url, 'http://localhost:8983/solr/core0/update')
