# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import urlparse

from heat.tests.common import HeatTestCase
from heat.api.openstack.v1.views import views_common


class TestViewsCommon(HeatTestCase):
    def setUp(self):
        super(TestViewsCommon, self).setUp()
        self.request = mock.Mock()
        self.stack1 = {
            'id': 'id1',
        }
        self.stack2 = {
            'id': 'id2',
        }

    def setUpGetCollectionLinks(self):
        self.items = [self.stack1, self.stack2]
        self.request.params = {'limit': '2'}
        self.request.path_url = "http://example.com/fake/path"

    def test_get_collection_links_creates_next(self):
        self.setUpGetCollectionLinks()
        links = views_common.get_collection_links(self.request, self.items)

        expected = 'http://example.com/fake/path?marker=id2&limit=2'
        next_link = filter(lambda link: link['rel'] == 'next', links).pop()
        self.assertEqual('next', next_link['rel'])
        self.assertEqual(expected, next_link['href'])

    def test_get_collection_links_doesnt_create_next_if_no_limit(self):
        self.setUpGetCollectionLinks()
        del self.request.params['limit']
        links = views_common.get_collection_links(self.request, self.items)

        self.assertEqual([], links)

    def test_get_collection_links_doesnt_create_next_if_page_not_full(self):
        self.setUpGetCollectionLinks()
        self.request.params['limit'] = '10'
        links = views_common.get_collection_links(self.request, self.items)

        self.assertEqual([], links)

    def test_get_collection_links_overwrites_url_marker(self):
        self.setUpGetCollectionLinks()
        self.request.params = {'limit': '2', 'marker': 'some_marker'}
        links = views_common.get_collection_links(self.request, self.items)

        expected = 'http://example.com/fake/path?marker=id2&limit=2'
        next_link = filter(lambda link: link['rel'] == 'next', links).pop()
        self.assertEqual(expected, next_link['href'])

    def test_get_collection_links_does_not_overwrite_other_params(self):
        self.setUpGetCollectionLinks()
        self.request.params = {'limit': '2', 'foo': 'bar'}
        links = views_common.get_collection_links(self.request, self.items)

        next_link = filter(lambda link: link['rel'] == 'next', links).pop()
        url = next_link['href']
        query_string = urlparse.urlparse(url).query
        params = urlparse.parse_qs(query_string)
        self.assertEqual('2', params['limit'][0])
        self.assertEqual('bar', params['foo'][0])

    def test_get_collection_links_handles_invalid_limits(self):
        self.setUpGetCollectionLinks()
        self.request.params = {'limit': 'foo'}
        links = views_common.get_collection_links(self.request, self.items)
        self.assertEqual([], links)

        self.request.params = {'limit': None}
        links = views_common.get_collection_links(self.request, self.items)
        self.assertEqual([], links)
