import deploy
import getopt
import os
import requests
import sys
import time

docker_container_name = None
docker_envs = []
docker_volumes = []
docker_ports = []
docker_networks = []
docker_compose_file = None

def check(param, name):
    if not param:
        raise Exception("{} can't be null".format(name))

def parse_optional_args(argv):
    global docker_envs, docker_volumes, docker_ports, docker_networks, docker_compose_file, docker_container_name
    usage = 'Usage: main.py  \
            --docker_env=ASPNETCORE_ENVIRONMENT=Development \
            --net=bridge \
            --v=source:target \
            --port=8585:80 \
            --compose-file=docker-compose.yml'
    try:
        opts, args = getopt.getopt(argv,
                                   'p:e:v',
                                   ['env=', 'net=', 'port=', 'volume=', 'compose-file=', 'name=', 'container-name='])
    except getopt.GetoptError as er:
        print(er)
        print(usage)

        sys.exit(2)

    for opt, arg in opts:
        if opt in('--net'):
            docker_networks.append(str.strip(arg))
        elif opt in('--name', '--container-name'):
            docker_container_name = str.strip(arg)
        elif opt in('-p', '--port'):
            docker_ports.append(arg)
        elif opt in('-e', '--env'):
            docker_envs.append(str.strip(arg))
        elif opt in('-v', '--volume'):
            docker_volumes.append(str.strip(arg))
        elif opt in('--compose-file'):
            docker_compose_file = str.strip(arg)

if __name__ == '__main__':
    print("------------Portainer-Api------------")
    endpoint_name = os.environ.get('PORTAINER_ENDPOINT')
    check(endpoint_name, 'PORTAINER_ENDPOINT')
    container_name = os.environ.get('PROJECT_NAME')
    check(container_name, 'PROJECT_NAME')
    image = os.environ.get('DOCKER_IMAGE')
    check(image, 'DOCKER_IMAGE')
    if len(sys.argv) > 1:
        parse_optional_args(sys.argv[1:])
    swarm_mode = os.environ.get('SWARM_MODE')
    if swarm_mode and swarm_mode.lower() == str(True).lower():
        print("Deploy project in swarm mode")
        check(docker_compose_file, 'DOCKER-COMPOSE FILE')
        deploy = deploy.Deploy(endpoint_name, container_name, image, None, None, None, None, container_name, docker_compose_file)
        deploy.deploy_stack()
    else:
        print("Deploy project in singleton mode")
        deploy = deploy.Deploy(endpoint_name, docker_container_name if docker_container_name else container_name, image, docker_networks, docker_ports, docker_volumes, docker_envs, None, None)
        deploy.deploy_container()
    
    print("------------Deploy completed------------")