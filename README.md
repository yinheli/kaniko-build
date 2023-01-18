# kaniko-build

这是一个 kaniko cli 工具，可以帮你快速把一个 `Dockerfile` 在 k8s 集群中打包生成镜像并推送到镜像库。 具体参考 [pod.yaml](./kanikobuild/resource/pod.yaml)

## 安装

```bash
pip install --upgrade git+https://github.com/yinheli/kaniko-build.git
```

## 依赖

- python3
- kubectl

## 准备工作

### secret

准备 `dockercred` secret 用于推送镜像

```bash
kubectl create secret -n default docker-registry dockercred \
    --docker-server=xxx \
    --docker-username=xxx \
    --docker-password=xxx
```

或者用 yaml 声明式创建

> `cat ~/.docker/config.json | base64 -w0`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dockercred
  namespace: default
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: >-
    xxx
```

## 相关资料

- kaniko https://github.com/GoogleContainerTools/kaniko
