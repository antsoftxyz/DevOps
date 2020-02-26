# Portainer Api

## 概述

Portainer Api 的目的是是将Docker服务部署到对应的平台上。

## 使用

#### 环境变量

Portainer Api使用了大量的环境变量，作为部署参数。使用环境变量的主要原因是为了利用Jenkins的Credentials功能保护Portainer的Secret；另一部分原因是为了公用CI部分的一些参数。

环境变量列表：

* PROJECT_NAME （项目名称）
* PORTAINER_URL （Portainer地址）
* PORTAINER_USERNAME （Portainer用户名）
* PORTAINER_PASSWORD （Portainer密码）
* PORTAINER_ENDPOINT （Portainer节点名称）
* REGISTRY_HOST （Docker Registry地址）
* REGISTRY_GROUP （Docker Registry的Group）
* REGISTRY_USERNAME （Docker Registry用户名）
* REGISTRY_PASSWORD （Docker Registry密码）
* SWARM_MODE （是否启用Swarm）
* DOCKER_IMAGE （Docker镜像）

命令行参数列表：

* --net （指定Container或Service加入的网络，支持多个参数，对于Service仅在创建时有效）
* --name（Container或Service名称，可选参数，默认使用PROJECT_NAME)
* -port / -p （指定Container或Service暴露的端口，支持多个参数，对于Service仅在创建时有效）
* -env / -e （指定Container或Service环境变量，支持多个参数，对于Service仅在创建时有效）
* --volume / -v （指定Container需要映射的目录，支持多个参数，仅对Container有效）
* --memory （指定Container或Service的最大内存使用，对于Container和Service都有效）
* --mode （指定Service的模式Replicated或Global，仅创建Service时有效，默认值Replicated）
* --replicas （指定Service的Replicas，仅创建Service且mode=Replicated时有效，默认值1）
* --stack-name （指定Stack名称，更新Stack内Service或部署Stack时使用）
* --compose-file （指定部署Stack的docker-compose文件）

#### 使用

Portainer Api支持Container部署、Service创建、Service更新、Stack部署与更新，下面分别介绍这四种模式。

* #### Container部署

    ```bash
    python /src/main.py --name=peck --net=app --env=ASPNETCORE_ENVIRONMENT=Development --port=12345:80 --net=app-swarm
    ```

* #### Service创建

    Service只有在创建时支持指定network、environment、port，更新Services时只支持更新image和memory-limit

    ***环境变量SWARM_MODE必须为TRUE***

    ```bash
    python /src/main.py --name=peck --net=app --env=ASPNETCORE_ENVIRONMENT=Development --port=12345:80 --net=app-swarm
    ```

* #### Service更新

    ***环境变量SWARM_MODE必须为TRUE，更新Stack内的Service时需要指定StackName***

    ***目前仅支持更新服务的image、memory-limit***

    1. 更新独立的服务

    ```bash
    python /src/main.py --name=peck --memory-limit=209715200
    ```

    2. 更新Stack中的服务

        仅服务的image
        ```bash
        python /src/main.py --name=peck --stack_name=pipeline
        ```

        更新服务的image和memory-limit
        ```bash
        python /src/main.py --name=peck --stack_name=pipeline --memory-limit=209715200
        ```

* #### Stack部署或更新

    ***环境变量SWARM_MODE必须为TRUE***

    ***该模式仅用于初始化一套全新的环境时使用，且不会多次使用***

    ***正常情况下，PROD或DEV环境的发布，应该走更新Service的模式，而非该模式***

    ```bash
    python /src/main.py --compose-file=docker-compose.deploy.yml --stack-name=fengchao
    ```