#! /usr/bin/python
import requests
import json
import sys
import time
from st2actions.runners.pythonrunner import Action
from novaclient.client import Client


class OpenstackInstance(Action):
    def __init__(self, config: object = None):
        super(OpenstackInstance, self).__init__(config=config)

    def run(self, **kwargs):
        self.compute_host = kwargs.get('compute_host_ipaddr')
        # Alternative way to import credentials:
        # self.credentials_new = {input_params: value for input_params, value in kwargs.items()}
        assert isinstance(self._get_project_name, object)
        self.credentials = {
            'version': kwargs['version']
            'username': kwargs['username'],
            'password': kwargs['password'],
            'auth_url': kwargs['auth_url'],
            'project_id': self._get_project_name
        }
        self.nova_client = Client(**self.credentials)
        self.instance_attrs = {
            'image': self.nova_client.images.find(name=kwargs.get('image', 'cirros')),
            'flavor': self.nova_client.flavors.find(name=kwargs.get('flavor', 'm1.tiny')),
            'net': self.nova_client.networks.find(label=kwargs.get('network_name', 'private')),
            'key_name': kwargs.get('key_name'),
            'instance_name': kwargs.get('instance_name', "{}_instance".format(self.credentials['username']))
        }
        self.create_instance(self.instance_attrs)



    def create_instance(self, **instance_attrs):
        nics = [{'net-id': instance_attrs['net'].id}]
        try:
            self.nova_client.servers.create(nics=nics, **instance_attrs)
            self.logger.info("Creating VM instance {}".format(instance_attrs['name']))
            time.sleep(10)
        except ValueError as err:
            self.logger.error("Failed to create instance {}\nError: {}".format(instance_attrs['name'], err))
        if instance_attrs['name'] in self.nova_client.servers.list():
            self.logger.info("Instance created successfully")
            return
        else:
            self.logging.error("Failed to create instance {}".format(instance_attrs['name']))
            sys.exit(1)

    @property
    def _get_project_name(self):
        token_url = "http://{}:5000/v2.0/tokens".format(self.compute_host)
        headers = {'Content-Type': 'application/json'}
        payload = {
            'auth': {
                'passwordCredentials': {
                    'username': self.credentials.get('username'),
                    'password': self.credentials.get('password')
                }
            }
        }
        request = requests.post(token_url, headers=headers, data=json.dumps(payload))
        if not request.status_code == 200:
            self.logger.error('Failed to get Keystone Identity token')
            request.raise_for_status()
            sys.exit(1)
        response = request.json()
        return response['access']['token']['id']



