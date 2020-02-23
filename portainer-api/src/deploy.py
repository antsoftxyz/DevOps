#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" portainer-api """

import base64
import hashlib
import requests
import json
import yaml
import time
import config

class Deploy:
    def __init__(self, endpoint_name, container_name, image, networks, ports, volumes, envs, stack_name, compose_file):
        config.loadConfigFromEnv()
        self.config = config
        self.container_name = container_name
        self.image = image
        self.networks = networks
        self.ports = ports
        self.volumes = volumes
        self.envs = envs
        self.portainer_token = self.auth_portainer()
        self.registry_token = self.auth_registry()
        self.endpoint_id = self.parse_endpoint_id(endpoint_name)
        self.docker_api_prefix = '{}/api/endpoints/{}/docker'.format(
            self.config.portainer_url, self.endpoint_id)
        self.auth_portainer()
        self.stack_name = stack_name
        import os
        print(os.getcwd())
        if compose_file:
            self.compose_file = open(compose_file, 'r').read()
        self.stack_api_prefix = '{}/api/stacks'.format(
            self.config.portainer_url)
        
    def auth_portainer(self):
        url = self.config.portainer_url + '/api/auth'
        payload = json.dumps({'Username': self.config.portainer_username, 'Password': self.config.portainer_password})
        headers = {'cache-control': 'no-cache'}

        response = requests.request(
            'POST',
            url,
            data = payload,
            headers = headers
        )
        response.raise_for_status()
        return json.loads(response.text)['jwt']

    def auth_registry(self):
        login_info = {
            'username': self.config.registry_username,
            'password': self.config.registry_password,
            'serveraddress': self.config.registry_host
        }
        login_info = json.dumps(login_info)
        return base64.b64encode(login_info.encode())

    def parse_endpoint_id(self, endpoint_name):
        url = self.config.portainer_url + '/api/endpoints'
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache',
        }
        response = requests.request('GET', url, headers = headers)
        response.raise_for_status()
        endpoints = response.json()
        for endpoint in endpoints:
            if endpoint['Name'].lower() == endpoint_name.lower():
                return endpoint['Id']
        
        raise Exception('can not find {} endpoint'.format(endpoint_name))

    def warmup(self):
        retry = 0
        while retry < 3:
            try:
                url = '{0}/containers/json'.format(self.docker_api_prefix)
                headers = {
                    'authorization': self.portainer_token,
                    'content-type': 'application/json',
                    'cache-control': 'no-cache',
                }
                response = requests.request(
                    'GET', url, headers=headers, timeout=5)
                response.raise_for_status()
                break
            except Exception:
                pass
            retry += 1

    def pull_image(self, image_name = None):
        '''
        pull image from docker registry
        '''
        url = '{}/images/create'.format(self.docker_api_prefix)

        if not image_name:
            image_name = self.image

        if ':' not in image_name: # If image does not contains a tag
            image_name += ':latest'
        
        name, tag = image_name.split(':')
        queryString = { 'fromImage': '{}'.format(name), 'tag': tag }
        
        print(queryString)
        headers = {
            'authorization': self.portainer_token,
            'X-Registry-Auth': self.registry_token if image_name.startswith(self.config.registry_host) else None,
            'cache-control': 'no-cache',
        }

        result = False
        retry = 0
        while retry < 3:
            try:
                response = requests.request(
                    'POST', url, headers=headers, params=queryString, timeout=30 * (1 + retry))
                print(response.text)
                if response.status_code < 300:
                    result = True
                    break
            except Exception:
                pass
            retry += 1
        if result == False:
            raise Exception("Pull image failed")

    def update_restart_policy(self):
        url = '{}/containers/{}/update'.format(
            self.docker_api_prefix, self.container_name)
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache',
        }
        payload = {
            'RestartPolicy': {
                'MaximumRetryCount': 1,
                'Name': 'on-failure'
            }
        }
        payload = json.dumps(payload)
        response = requests.request('POST', url, headers=headers, params='')
        print('cancel restart=always:' + response.text)

    def stop_container(self):
        url = '{}/containers/{}/stop'.format(self.docker_api_prefix,
                                             self.container_name)
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache',
        }
        requests.request('POST', url, headers=headers, params=None)

    def delete_container(self, force = True):
        url = '{}/containers/{}'.format(self.docker_api_prefix, self.container_name)
        queryString = {'force': force}
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache',
        }
        try:
            response = requests.request('DELETE', url, headers=headers, params=queryString)
            print(response.text)
        except Exception as ex:
            if response.status_code != 404:
                print('Container not exists')
            else:
                raise ex

    def create_container(self):
        url = '{0}/containers/create'.format(self.docker_api_prefix)
        queryString = {'name': self.container_name}
        portBindings = {}
        exposedPorts = {}
        if self.ports and len(self.ports):
            for port in self.ports:
                pubPort, internalPort = port.split(':')
                exposedPorts[internalPort + '/tcp'] = {}
                portBindings[internalPort + '/tcp'] = [
                    { 'HostPort': pubPort}
                ]

        binds = []
        if self.volumes and len(self.volumes):
            for volume in self.volumes:
                binds.append(volume)

        defaultNetwork = self.networks.pop(0) if self.networks and len(self.networks) else 'default'

        payload = {
            'Env': self.envs,
            'Image': self.image,
            'ExposedPorts': exposedPorts,
            'HostConfig': {
                'Binds': binds,
                'NetworkMode': defaultNetwork,
                'PortBindings': portBindings,
                'RestartPolicy': {
                    'Name': 'always',
                    'MaximumRetryCount': 0
                }
            }
        }

        payload = json.dumps(payload)
        print(payload)
        headers = {
            'authorization': self.portainer_token,
            'content-type': 'application/json',
            'cache-control': 'no-cache',
        }
        response = requests.request(
            'POST', url, data=payload, headers=headers, params=queryString)
        print(response.text)
        
        # connect to networks
        while self.networks and len(self.networks):
            self.join_network(self.networks.pop(0), response.json()['Id'])

    def join_network(self, network_name, container_id):
        url = '{}/networks/{}/connect'.format(self.docker_api_prefix, network_name)
        headers = {
            'authorization': self.portainer_token,
            'content-type': 'application/json',
            'cache-control': 'no-cache',
        }
        payload = {
            'Container': container_id
        }
        payload = json.dumps(payload)
        response = requests.request('POST', url, headers=headers, data=payload)
        response.raise_for_status() 
        print('join network ' + network_name + ' success.')

    def start_container(self):
        url = '{}/containers/{}/start'.format(self.docker_api_prefix, self.container_name)
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache'
        }
        response = requests.request('POST', url, headers=headers)
        response.raise_for_status()

    def swarm_id(self):
        url = '{}/swarm'.format(self.docker_api_prefix)
        headers = {
            'authorization': self.portainer_token
        }
        response = requests.request('GET', url, headers=headers)
        response.raise_for_status()
        swarm_dict = response.json()
        return swarm_dict["ID"]

    def stack_exists(self):
        url = self.stack_api_prefix
        headers = {
            'authorization': self.portainer_token
        }
        response = requests.request('GET', url, headers=headers)
        response.raise_for_status()
        stacks = response.json()
        for stack in stacks:
            if stack["Name"] == self.stack_name:
                return True
        
        return False

    def stack_id(self):
        url = self.stack_api_prefix
        headers = {
            'authorization': self.portainer_token
        }
        response = requests.request('GET', url, headers=headers)
        response.raise_for_status()
        stacks = response.json()
        for stack in stacks:
            if stack["Name"] == self.stack_name:
                return stack["Id"]

    def create_stack(self):
        url = self.stack_api_prefix
        queryString = {'method': 'string', 'type': 1, 'endpointId': self.endpoint_id}

        swarm_id = self.swarm_id()
        if not swarm_id:
            swarm_id = hashlib.sha224(str(self.stack_name).encode()).hexdigest()

        payload = {
            'Name': self.stack_name,
            'SwarmID': swarm_id,
            # convert to raw string that contains space and '/n '
            'StackFileContent': self.compose_file  # repr(self.compose_file)
        }
        payload = json.dumps(payload)

        headers = { 'authorization': self.portainer_token }
        response = requests.request(
            'POST', url, data=payload, headers=headers, params=queryString)
        response.raise_for_status()
        print(response.text)

    def update_stack(self):
        stack_id = self.stack_id()
        url = '{}/{}'.format(self.stack_api_prefix, stack_id)
        queryString = {'endpointId': self.endpoint_id}
        headers = { 'authorization': self.portainer_token }
        payload = {
            'StackFileContent': self.compose_file  # repr(self.compose_file)
        }
        payload = json.dumps(payload)
        response = requests.request(
            'PUT', url, data=payload, headers=headers, params=queryString)
        response.raise_for_status()
        print(response.text)

    def pull_stack_images(self):
        compose_dict = yaml.load(self.compose_file, Loader=yaml.FullLoader)
        for service in compose_dict['services']:
            image = compose_dict['services'][service]['image']
            self.pull_image(image)

    '''
    Deploy container
    '''
    def deploy_container(self):
        self.warmup()
        print('warmup successfully')

        self.pull_image()
        print('pull image successfully')

        self.delete_container()
        print('delete container successfully')

        self.create_container()
        print('create container successfully')

        self.start_container()
        print('start container successfully')

        print('deploy finished')

    def deploy_stack(self):
        self.warmup()
        print('warmup successfully')

        self.pull_stack_images()
        print('pull stack images successfully')

        if not self.stack_exists():
            self.create_stack()
            print('create stack successfully')
        else:
            self.update_stack()
            print('update stack successfully')


if __name__ =='__main__':
    import sys
    deploy = Deploy('local', 'hello', 'yunfandev/pipeline:dev', None, None, None, None, None, None, None)
    deploy.deploy_container()