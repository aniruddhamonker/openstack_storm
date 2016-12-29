#! /usr/bin/python
import requests
import json
import sys
import time
from st2actions.runners.pythonrunner import Action
from novaclient.client import Client


class OpenstackInstance(Action):
    def __init__(self, config=None):
        super(OpenstackInstance, self).__init__(config=config)

    def run(self, auth_url, password, username, version,
            instance_name="{}_instance".format(self.credentials['username']), key_name=None, network_name='private',
            flavor='m1.tiny', image='cirros', **kwargs):
        # Alternative way to import credentials:
        # self.credentials_new = {input_params: value for input_params, value in kwargs.items()}
        self.credentials = {
            'version': version,
            'username': username,
            'api_key': password,
            'auth_url': auth_url,
            'project_id': self.get_tenant_name(**kwargs)
        }
        try:
            self.nova_client = Client(**self.credentials)
            self.logger.info("Authentication of nova client successful")
        except Exception as err:
            self.logger.error("Creating nova client failed with {} : {}".format(type(err),err))
            
        self.instance_attrs = {
            'image': self.nova_client.images.find(name=image),
            'flavor': self.nova_client.flavors.find(name=flavor),
            'net': self.nova_client.networks.find(label=network_name),
            'key_name': key_name,
            'name': instance_name
        }
        
        self.create_instance(**self.instance_attrs)
            
    def create_instance(self, **instance_attrs):
        """
        :rtype: class novaclient.base.ListWithMeta
        """
        instance_attrs['nics'] = [{'net-id': instance_attrs['net'].id}]
        try:
            self.nova_client.servers.create(**instance_attrs)
            self.logger.info("Creating VM instance {}".format(instance_attrs['name']))
            time.sleep(10)
        except Exception as err:
            print("Failed to create instance {}\nError: {}--> {}".format(instance_attrs['name'], type(err), err))

        instances = self.nova_client.servers.list()
        if instance_attrs['name'] in [i.name for i in instances]:
            self.logger.info("Instance created successfully")
            return instances
        else:
            self.logger.error("Failed to create instance {}".format(instance_attrs['name']))

    def get_tenant_name(self, **credentials):
        token_url = "http://{}:5000/v2.0/tokens".format(credentials['compute_host_ipaddr'])
        headers = {'Content-Type': 'application/json'}
        payload = {
            'auth': {
                'passwordCredentials': {
                    'username': credentials['username'],
                    'password': credentials['password']
                }
            }
        }
        request = requests.post(token_url, headers=headers, data=json.dumps(payload))
        if not request.status_code == 200:
            self.logger.error('Failed to get Keystone Identity token')
            request.raise_for_status()
            sys.exit(1)
        response = request.json()
        return response['access']['user']['name']



