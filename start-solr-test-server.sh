#!/bin/bash

set -e

cd $(dirname $0)

export TEST_ROOT=$(pwd)

mkdir -p "test-solr-server"
cd "test-solr-server"

export SOLR_ARCHIVE="solr-${SOLR_VERSION}.tgz"
export SOLR_DIR="solr-${SOLR_VERSION}"

# ensure we have the Solr tarball
if [ -d "${HOME}/download-cache/" ]; then
    export SOLR_ARCHIVE="${HOME}/download-cache/${SOLR_ARCHIVE}"
fi

if [ -f ${SOLR_ARCHIVE} ]; then
    # If the tarball doesn't extract cleanly, remove it so it'll download again:
    tar -tf ${SOLR_ARCHIVE} > /dev/null || rm ${SOLR_ARCHIVE}
fi

if [ ! -f ${SOLR_ARCHIVE} ]; then
    # SOLR_DOWNLOAD_URL=$(python get-solr-download-url.py $SOLR_VERSION)
    # TODO: see if you can make the URL-getter work again
    SOLR_DOWNLOAD_URL="https://archive.apache.org/dist/lucene/solr/${SOLR_VERSION}/solr-${SOLR_VERSION}.tgz"
    curl -Lo $SOLR_ARCHIVE ${SOLR_DOWNLOAD_URL} || (echo "Unable to download ${SOLR_DOWNLOAD_URL}"; exit 2)
fi

echo "Extracting Solr ${SOLR_VERSION} to ${SOLR_DIR}/"
rm -rf ${SOLR_DIR}
mkdir ${SOLR_DIR}
tar -xf ${SOLR_ARCHIVE}

echo "Configuring Solr"
cd ${SOLR_DIR}
# The example configs are different in Solr 4 and 5. This bit of trickery makes them the same.
if [[ $SOLR_VERSION == 5* ]]; then
    mkdir -p server/solr/collection1
    mv server/solr/configsets/basic_configs/conf server/solr/collection1
    echo "name=collection1" > server/solr/collection1/core.properties
    python "../../tests/amend_schema.py"
else
    mv "example" "server"
fi

# Add MoreLikeThis handler
perl -p -i -e 's|<!-- Search Components|<!-- More like this request handler -->\n  <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />\n\n\n  <!-- Search Components|'g server/solr/collection1/conf/solrconfig.xml

echo 'Starting server'
# We use exec to allow process monitors to correctly kill the
# actual Java process rather than this launcher script:
cd server
exec java -Djava.awt.headless=true -Dapple.awt.UIElement=true -jar start.jar --module=http
