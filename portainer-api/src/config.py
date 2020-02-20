#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" load config """

import os

portainer_url = 'PORTAINER_URL'
portainer_username = 'PORTAINER_USERNAME'
portainer_password = 'PORTAINER_PASSWORD'
registry_host = 'REGISTRY_HOST'
registry_group = 'REGISTRY_GROUP'
registry_username = 'REGISTRY_USERNAME'
registry_password = 'REGISTRY_PASSWORD'

def loadConfigFromEnv():
    global portainer_url, portainer_username, portainer_password, registry_host, registry_group, registry_username, registry_password
    portainer_url = os.environ.get('PORTAINER_URL')
    portainer_username = os.environ.get('PORTAINER_USERNAME')
    portainer_password = os.environ.get('PORTAINER_PASSWORD')
    registry_host = os.environ.get('REGISTRY_HOST')
    registry_group = os.environ.get('REGISTRY_GROUP')
    registry_username = os.environ.get('REGISTRY_USERNAME')
    registry_password = os.environ.get('REGISTRY_PASSWORD')

if __name__ =='__main__':
    import sys
    loadConfigFromEnv()
    print(locals())