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
docker_stack_name = None
docker_memory_limit = 0
docker_service_mode = "Replicated"
docker_replicas = 1

def check(param, name):
    if not param:
        raise Exception("{} can't be null".format(name))

def parse_optional_args(argv):
    global docker_envs, docker_volumes, docker_ports, docker_networks, docker_compose_file, docker_container_name, docker_stack_name, docker_memory_limit, docker_service_mode, docker_replicas
    usage = 'Usage: main.py  \
            --docker_env=ASPNETCORE_ENVIRONMENT=Development \
            --net=bridge \
            --v=source:target \
            --port=8585:80 \
            --compose-file=docker-compose.yml'
    try:
        opts, args = getopt.getopt(argv,
                                   'p:e:v',
                                   ['env=', 'net=', 'port=', 'volume=', 'compose-file=', 'name=', 'container-name=', 'stack-name=', 'memory=', 'limit-memory=', 'mode=', 'replicas='])
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
        elif opt in('--stack-name'):
            docker_stack_name = str.strip(arg)
        elif opt in('--memory', '--limit-memory'):
            docker_memory_limit = int(str.strip(arg))
        elif opt in('--mode'):
            docker_service_mode = str.strip(arg)
        elif opt in('--replicas'):
            docker_replicas = int(str.strip(arg))

if __name__ == '__main__':
    print("------------Portainer-Api------------")

    # Get required env
    endpoint_name = os.environ.get('PORTAINER_ENDPOINT')
    check(endpoint_name, 'PORTAINER_ENDPOINT')
    docker_container_name = os.environ.get('PROJECT_NAME')
    check(docker_container_name, 'PROJECT_NAME')
    swarm_mode = os.environ.get('SWARM_MODE')
    image = os.environ.get('DOCKER_IMAGE')

    # Parse commandline arguments
    if len(sys.argv) > 1:
        parse_optional_args(sys.argv[1:])
    
    # Swarm mode
    if swarm_mode and swarm_mode.lower() == str(True).lower():
        if docker_compose_file:
            check(docker_stack_name, 'STACK_NAME')
            print("------------Deploy stack------------")
            deploy = deploy.Deploy(endpoint_name, docker_container_name, None, None, None, None, None, docker_stack_name, docker_compose_file, None)
            deploy.deploy_stack()
        else:
            check(image, 'DOCKER_IMAGE')
            print("------------Deploy service------------")
            deploy = deploy.Deploy(endpoint_name, docker_container_name, image, docker_networks, docker_ports, docker_volumes, docker_envs, docker_stack_name, docker_compose_file, docker_memory_limit)
            deploy.deploy_service(docker_service_mode, docker_replicas)
    else:
        check(image, 'DOCKER_IMAGE')
        print("------------Deploy container------------")
        deploy = deploy.Deploy(endpoint_name, docker_container_name, image, docker_networks, docker_ports, docker_volumes, docker_envs, None, None, docker_memory_limit)
        deploy.deploy_container()
    
    print("------------Deploy completed------------")