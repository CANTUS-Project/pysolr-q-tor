#!/usr/bin/env python

from xml.etree import ElementTree as etree

schema_path = 'server/solr/collection1/conf/schema.xml'

schema = etree.parse(schema_path)
root = schema.getroot()

if 'schema' == root.tag:
    root.append(etree.Element('field', {'name': 'title', 'type': 'text_general', 'indexed': 'true',
                                        'stored': 'true', 'multiValued': 'true'}))
    root.append(etree.Element('field', {'name': 'price', 'type': 'float', 'indexed': 'true',
                                        'stored': 'true'}))
    root.append(etree.Element('field', {'name': 'popularity', 'type': 'int', 'indexed': 'true',
                                        'stored': 'true'}))
    root.append(etree.Element('field', {'name': 'text', 'type': 'text_general', 'indexed': 'true',
                                        'stored': 'false', 'multiValued': 'true'}))
    schema.write(schema_path)
else:
    # guess all the tests will fail...
    raise SystemExit(1)
