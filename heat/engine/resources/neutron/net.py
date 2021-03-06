# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
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

from heat.engine import clients
from heat.openstack.common import log as logging
from heat.engine.resources.neutron import neutron
from heat.engine import properties

if clients.neutronclient is not None:
    import neutronclient.common.exceptions as neutron_exp
    from neutronclient.neutron import v2_0 as neutronV20

logger = logging.getLogger(__name__)


class Net(neutron.NeutronResource):
    PROPERTIES = (
        NAME, VALUE_SPECS, ADMIN_STATE_UP, TENANT_ID, SHARED,
    ) = (
        'name', 'value_specs', 'admin_state_up', 'tenant_id', 'shared',
    )

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('A string specifying a symbolic name for the network, which is '
              'not required to be unique.'),
            update_allowed=True
        ),
        VALUE_SPECS: properties.Schema(
            properties.Schema.MAP,
            _('Extra parameters to include in the "network" object in the '
              'creation request. Parameters are often specific to installed '
              'hardware or extensions.'),
            default={},
            update_allowed=True
        ),
        ADMIN_STATE_UP: properties.Schema(
            properties.Schema.BOOLEAN,
            _('A boolean value specifying the administrative status of the '
              'network.'),
            default=True,
            update_allowed=True
        ),
        TENANT_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the tenant which will own the network. Only '
              'administrative users can set the tenant identifier; this '
              'cannot be changed using authorization policies.')
        ),
        SHARED: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether this network should be shared across all tenants. '
              'Note that the default policy setting restricts usage of this '
              'attribute to administrative users only.'),
            default=False,
            update_allowed=True
        ),
    }

    attributes_schema = {
        "status": _("The status of the network."),
        "name": _("The name of the network."),
        "subnets": _("Subnets of this network."),
        "admin_state_up": _("The administrative status of the network."),
        "tenant_id": _("The tenant owning this network."),
        "show": _("All attributes."),
    }

    update_allowed_keys = ('Properties',)

    def handle_create(self):
        props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())
        net = self.neutron().create_network({'network': props})['network']
        self.resource_id_set(net['id'])

    def _show_resource(self):
        return self.neutron().show_network(
            self.resource_id)['network']

    def check_create_complete(self, *args):
        attributes = self._show_resource()
        return self.is_built(attributes)

    def handle_delete(self):
        client = self.neutron()
        try:
            client.delete_network(self.resource_id)
        except neutron_exp.NeutronClientException as ex:
            self._handle_not_found_exception(ex)
        else:
            return self._delete_task()

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        props = self.prepare_update_properties(json_snippet)

        self.neutron().update_network(self.resource_id, {'network': props})

    def check_update_complete(self, *args):
        attributes = self._show_resource()
        return self.is_built(attributes)

    def _handle_not_found_exception(self, ex):
        # raise any exception which is not for a not found network
        if not (ex.status_code == 404 or
                isinstance(ex, neutron_exp.NetworkNotFoundClient)):
            raise ex


class NetDHCPAgent(neutron.NeutronResource):
    PROPERTIES = (
        NETWORK_ID, DHCP_AGENT_ID,
    ) = (
        'network_id', 'dhcp_agent_id',
    )

    properties_schema = {
        NETWORK_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the network you want to be scheduled by the '
              'dhcp_agent. Note that the default policy setting in Neutron '
              'restricts usage of this property to administrative users '
              'only.'),
            required=True
        ),
        DHCP_AGENT_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the dhcp-agent to schedule the network. Note that '
              'the default policy setting in Neutron restricts usage of this '
              'property to administrative users only.'),
            required=True
        ),
    }

    def handle_create(self):
        network_id = self.properties[self.NETWORK_ID]
        dhcp_agent_id = self.properties[self.DHCP_AGENT_ID]
        try:
            self.neutron().add_network_to_dhcp_agent(
                dhcp_agent_id, {'network_id': network_id})
        except neutron_exp.NeutronClientException as ex:
            # if 409 is happened, the agent is already associated.
            if ex.status_code != 409:
                raise ex
        self.resource_id_set('%(net)s:%(agt)s' %
                             {'net': network_id, 'agt': dhcp_agent_id})

    def handle_delete(self):
        if not self.resource_id:
            return
        client = self.neutron()
        network_id, dhcp_agent_id = self.resource_id.split(':')
        try:
            client.remove_network_from_dhcp_agent(
                dhcp_agent_id, network_id)
        except neutron_exp.NeutronClientException as ex:
            # assume 2 patterns about status_code following:
            #  404: the network or agent is already gone
            #  409: the network isn't scheduled by the dhcp_agent
            if ex.status_code not in (404, 409):
                raise ex


class NetworkConstraint(object):

    def validate(self, value, context):
        try:
            neutron_client = clients.Clients(context).neutron()
            neutronV20.find_resourceid_by_name_or_id(
                neutron_client, 'network', value)
        except neutron_exp.NeutronClientException:
            return False
        else:
            return True


def constraint_mapping():
    if clients.neutronclient is None:
        return {}
    return {'neutron.network': NetworkConstraint}


def resource_mapping():
    if clients.neutronclient is None:
        return {}

    return {
        'OS::Neutron::Net': Net,
        'OS::Neutron::NetDHCPAgent': NetDHCPAgent,
    }
