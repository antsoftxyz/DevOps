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

#### 使用

Portainer Api支持两种部署方式：Singleton模式和Swarm模式，由于这两种模式有些各自的参数加之有些参数在CI部分不会用到，所以这一部分的参数不使用环境变量，转而使用命令行参数实现。

* Singleton模式

```bash
python /src/main.py --container-name=peck --net=app --env=ASPNETCORE_ENVIRONMENT=Development --port=12345:80 --net=app-swarm
```
* Swarm模式

```bash
python /src/main.py --compose-file=docker-compose.deploy.yml
```