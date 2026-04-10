# 1.需求简述

中间件对接硬件,提供统一规范的接口(bar_middleware)

    - 基于现有未来已知硬件适配需求,抽离出一个 middleware 对接设备硬件,对外提供标准接口,屏蔽不同硬件类型、业务逻辑、协议等诸多差异
    - 通过配置参数控制与仿真程序交互还是与真实设备交互
    - 通过配置参数控制启用哪一个硬件设备(因同一个功能,会有不同的硬件设备支持)

# 2.设计理念

1. 较少层级的封装,代码清晰简洁
2. 基础公共包: 日志工具、程序运行环境、web静态资源、硬件模块 指令执行,状态机 一层薄封装
3. 短平快的开发节奏,尽可能的按照一个模块一个包的理念组织代码,一个包仅对基础公共包有依赖

# 3.技术栈与开发环境

1. 编程语言: python3.10
2. web框架: fastapi
3. 通讯相关: tcp、udp、websocket、opcua、http
4. 开发工具: 推荐使用pycharm
5. 包管理工具: python自带pip
6. 操作系统: win、macos、linux 兼容

# 4.架构简述

## 1. 架构图

原设计一个项目包括仿真与 此 bar_middleware,后来把二者拆分。

![img.png](doc/reource/img.png)

## 2. 整体结构

![img.png](doc/reource/img1.png)

# 5. 开发环境搭建

直接安装python解释器或者使用conda、创建虚拟环境,不再赘述, 需python版本>=3.10

1. 克隆该项目到本地

      ```shell
      git clone https://codeup.aliyun.com/62b67c74e4166464dc3113e7/bar_platform.git
      ```

2. 激活python虚拟环境 : 不再赘述


3. 安装依赖

      ```shell
      cd bar_platform
      python3 install_pkg.py  # 该脚本指定了清华源加速,执行时无反应,查看是否为使用代理的问题
      ```

   至此,环境配置完成

# 6. 仿真程序说明

## 1. 结构

![img.png](doc/reource/img2.png)

## 2. 参数

运行在开发者本地,随时临时修改,无参数设置

## 3. 部署

运行在开发者本地,无需编译与部署,源码运行即可

## 4. 使用

1. 运行: `python3 main_bar_middleware.py`
2. 浏览器输入 `127.0.0.1:8002/docs` 进入swagger页面
   ![img_1.png](doc/reource/img_4.png)
3. 浏览器输入 `127.0.0.1:8002/redoc` 进入接口文档页面
   ![img.png](doc/reource/img_5.png)

# 8.中间件程序说明

## 1. 结构

![img.png](doc/reource/img3.png)

## 2.参数

   ```toml
# 针对中间件程序 bar_middleware 的配置参数

# 使用frank机械臂  1:启用 0:不启用  多个机械臂只能使用一个,若同时配置1,则使用第一个配置
use_arm_franka = 1

# 使用越江机械臂   1:启用 0:不启用
use_arm_yueJiang = 0

# 是否仿真模式运行  0:真机模式  1:仿真模式
simulation = 1

# 是否开放htpp接口 0:不开放http接口 1:开放http接口  开放时网页swagger可灵活操作硬件设备(后门~^_^~),投产时请关闭该项
use_http_api = 1
```

## 3. 部署

**前提:** 1. python3.10环境 2. 若初次部署,设备需要能连接外网,下载第三方依赖

脚本会自动识别是否初次部署,并做对应操作,无需考虑配置问题

_TODO : 做成脚本,支持ssh远程部署_

1. 获取权限: `sudo su`
2. 执行`python3 build_bar_middleware.py` 构建出程序包 bar_middleware.zip
3. 上传 bar_middleware.zip 程序包到机器部署目录: /home/deploy
4. 解压: `cd /home/deploy && unzip bar_middleware.zip`
5. 执行部署脚本: `cd /home/deploy/bar_middleware && python3 build_bar_middleware.py`

## 4. 使用

1. 本机运行: `python3 main_bar_middleware.py`
2. 真实设备上运行: `cd /mnt/smyze/apps/bar_middleware && bash start.sh`
    - 按需修改对应配置参数,修改完重启该程,执行 `bash start.sh `即可
3. 浏览器输入 `设备/本机ip:8003/docs` 进入swagger页面

- ![img.png](doc/reource/img_6.png)

4. 浏览器输入 `设备/本机ip:8003/redoc` 进入接口文档页面

- ![img.png](doc/reource/img_7.png)


