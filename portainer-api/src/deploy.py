#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" portainer-api """

import base64
import hashlib
import requests
import json
import os
import yaml
import time

class Deploy:
    def __init__(self, endpoint_name, container_name, image, networks, ports, volumes, envs, stack_name, compose_file, memory_limit):
        self.read_env()
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
            self.portainer_url, self.endpoint_id)
        self.auth_portainer()
        self.stack_name = stack_name
        if compose_file:
            self.compose_file = open(compose_file, 'r').read()
        self.stack_api_prefix = '{}/api/stacks'.format(
            self.portainer_url)
        self.memory_limit = memory_limit

    def read_env(self):
        self.portainer_url = os.environ.get('PORTAINER_URL')
        self.portainer_username = os.environ.get('PORTAINER_USERNAME')
        self.portainer_password = os.environ.get('PORTAINER_PASSWORD')
        self.registry_host = os.environ.get('REGISTRY_HOST')
        self.registry_group = os.environ.get('REGISTRY_GROUP')
        self.registry_username = os.environ.get('REGISTRY_USERNAME')
        self.registry_password = os.environ.get('REGISTRY_PASSWORD')
        
        
    def auth_portainer(self):
        url = self.portainer_url + '/api/auth'
        payload = json.dumps({'Username': self.portainer_username, 'Password': self.portainer_password})
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
            'username': self.registry_username,
            'password': self.registry_password,
            'serveraddress': self.registry_host
        }
        login_info = json.dumps(login_info)
        return base64.b64encode(login_info.encode())

    def parse_endpoint_id(self, endpoint_name):
        url = self.portainer_url + '/api/endpoints'
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

    def agents(self):
        agentURL = '{}/v2/agents'.format(self.docker_api_prefix)
        headers = {
            'authorization': self.portainer_token,
            'cache-control': 'no-cache',
        }

        response = requests.request('GET', agentURL, headers=headers)
        response.raise_for_status()
        return response.json()

    def pull_image(self, image_name = None, agent_node = None):
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
            'X-Registry-Auth': self.registry_token if image_name.startswith(self.registry_host) else None,
            'cache-control': 'no-cache',
        }

        if agent_node:
            headers["x-portaineragent-target"] = agent_node
            print("Pull image on {} node.".format(agent_node))

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
        else:
            # inspect image
            url = '{}/images/{}/json'.format(self.docker_api_prefix, image_name)
            response = requests.request('GET', url, headers=headers)
            response.raise_for_status()
            print("Pull image Id: {} successfully.\n".format(response.json()["Id"]) )

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
                },
                'Memory': self.memory_limit if self.memory_limit else 0
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

    def get_network(self, name):
        list_network_api = self.docker_api_prefix + '/networks'
        headers = {
            'authorization': self.portainer_token
        }
        response = requests.request('GET', list_network_api, headers=headers)
        response.raise_for_status()
        networks = response.json()
        for network in networks:
            if network["Name"] == name:
                return network

    def service_name(self):
        if self.stack_name:
            return self.stack_name + '_' + self.container_name
        else:
            return self.container_name

    def get_service(self):
        service_api = self.docker_api_prefix + '/services'
        headers = {
            'authorization': self.portainer_token
        }
        response = requests.request('GET', service_api, headers=headers)
        response.raise_for_status()
        services = response.json()
        for service in services:
            if service["Spec"]["Name"] == self.service_name():
                return service

    def create_service(self, mode = "Replicated", replicas = 1):
        create_service_api = self.docker_api_prefix + '/services/create'
        headers = {
            'authorization': self.portainer_token,
            'X-Registry-Auth': self.registry_token if self.image.startswith(self.registry_host) else None
        }
        payload = {
            'Name': self.service_name(),
            'TaskTemplate': {
                'ContainerSpec': {
                    'Image': self.image,
                    'Env': self.envs,
                },
                'Resources': {
                    'Limits': {
                        'MemoryBytes': self.memory_limit
                    }
                }
            }
        }

        # mode
        if mode:
            if mode == "Replicated":
                payload["Mode"] = {
                    "Replicated": {
                        "Replicas": replicas if replicas > 0 else 1
                    }
                }
            else:
                payload["Mode"] = {
                    "Global": {}
                }

        # attach network
        if self.networks and len(self.networks):
            payload["TaskTemplate"]["Networks"] = []
            for network in self.networks:
                network = self.get_network(network)
                if network:
                    payload["TaskTemplate"]["Networks"].append({
                        "Target": network["Id"]
                    })

        # port binding
        if self.ports and len(self.ports):
            payload["EndpointSpec"] = {
                'Mode': 'vip',
                'Ports': []
            }
            for port in self.ports:
                pubPort, internalPort = port.split(':')
                payload["EndpointSpec"]["Ports"].append(
                    {
                        'Protocol':'tcp',
                        'PublishMode': 'ingress',
                        'PublishedPort': int(pubPort),
                        'TargetPort': int(internalPort)
                    }
                )

        payload = json.dumps(payload)
        response = requests.request('POST', create_service_api, data = payload, headers=headers)
        response.raise_for_status()
        print(response.text)
        print('Create service successfully')

    '''
    Deploy service (image & memory limit)
    '''
    def deploy_service(self, mode = "Replicated", replicas = 1):
        self.warmup()
        self.pull_image()
        current_service = self.get_service()
        if not current_service:
            print("Service not exists!")
            print("Trying to create service: {}".format(self.service_name()))
            self.create_service(mode, replicas)
            return

        update_service_api = self.docker_api_prefix + '/services/' + current_service["ID"] + '/update'
        headers = {
            'authorization': self.portainer_token,
            'X-Registry-Auth': self.registry_token if self.image.startswith(self.registry_host) else None
        }

        queryString = {'version': current_service["Version"]["Index"]}

        payload = current_service["Spec"]
        payload["TaskTemplate"]["ContainerSpec"]["Image"] = self.image
        payload["TaskTemplate"]["ForceUpdate"] += 1
        if self.memory_limit > 0:
            if "Limits" in payload["TaskTemplate"]["Resources"]:
                payload["TaskTemplate"]["Resources"]["Limits"]["MemoryBytes"] = self.memory_limit
            else:
                payload["TaskTemplate"]["Resources"] = {
                    "Limits": {
                        "MemoryBytes": self.memory_limit
                    }
                }
        payload = json.dumps(payload)
        response = requests.request('POST', update_service_api, data = payload, headers=headers, params=queryString)
        response.raise_for_status()
        print(response.text)
        print('Update service {} successfully'.format(self.service_name()))

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
    deploy = Deploy('local', 'hello', 'registry.what.codes/peck/pipeline:dev', None, None, None, None, None, None, None)
    deploy.deploy_container()