# 小胖哥哥运维系统
>本人自学python，正好工作中使用saltstack，为了不生疏所学python所以自己弄了个平台，当做学习巩固知识。  
目前平台还在开发中并不是一个完成品，前端技术渣渣每次都要一点点设计页面和js耗时比写后端还久o(╯□╰)o 
   
>有兴趣的朋友可以参考一下&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;欢迎交流QQ:175714259

***
>**环境**：  
centos7.4  
python3.5.2  
django2.0.5  
saltstack version 2017.7.3  

***


>依赖软件安装：`yum install subversion rsync tcpdump -y `  

>数据库：mysql5.7.12-mysql8.0.11都可以，账号自行创建，新建一个数据库名`xpgg_oms`,编码字符集是`utf8mb4 -- UTF-8 Unicode`，排序是`utf8mb4_0900_ai_ci`   

>saltstack 自行安装配置不介绍，master主机至少须安装`salt-master、salt-minion、salt-api、salt-ssh`

***
## 项目安装
>如不熟悉则按下面步骤操作，熟悉的忽略
1. 先下载`requirements.txt`文件假设放在/tmp下，pip安装环境依赖包：  
`pip3 install -r /tmp/requirements.txt`  
2. 进入想要创建项目的文件夹，假设：`cd /usr/local/django/`  
3. 创建django项目，项目名xiaopgg_project：`django-admin.py startproject xiaopgg_project`  #django-admin.py在python3.5.2安装的bin目录下      
4. 进入项目目录`cd /usr/local/django/xiaopgg_project`  
5. 创建app，app名xpgg_oms：`python3 manage.py startapp xpgg_oms` #python3也是在python3.安装的bin目录下，最好加入环境变量方便使用  
6. 然后把git的文件覆盖到项目下即`/usr/local/django/xiaopgg_project/`下面  
7. `mkdir /usr/local/django/xiaopgg_project/logs` 日志目录创建必须提前创建不然项目启动会提示没有logs目录，如果需要修改日志目录则自行在settings.py里修改日志相关的配置

***
## 预配置
>修改配置settings.py文件  
``` python
vi /usr/local/django/xiaopgg_project/xpgg_oms/settings.py修改如下内容：
SITE_SALT_API_URL = 绑定salt-api的url  
SITE_SALT_MASTER = 绑定salt-master的minion_id  
SITE_SALT_API_NAME = 绑定salt-api的用户名  
SITE_SALT_API_PWD = 绑定salt-api的密码  
SITE_BASE_SVN_PATH = 绑定发布系统svn检出目录  
SITE_BASE_SVN_SYMLINK_PATH = 绑定发布系统同步文件临时目录  
数据库连接部分：
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'xpgg_oms',    
        'USER': 'xiaopgg',   #你的数据库用户名
        'PASSWORD': '123456', #你的数据库密码
        'HOST': '', #你的数据库主机，留空默认为localhost
        'PORT': '3306', #你的数据库端口,
```
>salt-master的配置文件添加svn同步文件临时目录
``` conf
vi /etc/salt/master 添加如下内容：
file_roots:
  svn:
    - /data/svn_symlink
```


***
## 初始化

***
以下操作都在`/usr/local/django/xiaopgg_project/`目录下执行  
>1.同步数据库： 
```
python3 manage.py makemigrations  
python3 manage.py migrate 
``` 
 
>2.添加管理员用户，`python3 manage.py createsuperuser` 按提示创建登录超级用户  

>3.启动项目： `python3 manage.py runserver 0.0.0.0:8000`  或者用supervisor开启项目，我是用supervisor来控制启动的  

>4.启动定时任务： `python3 manage.py crontab add` 定时获取minion信息配置

***
## 登录

***
>`http://你的ip:8000` #用上面创建的管理员用户登录即可

***
## salt相关

***
>平台上面salt相关的操作还需要从我另一个项目中下载srv里的sls文件配套使用，默认使用salt的base目录即/srv/salt/，从我的项目中直接下载即可

***
## 功能介绍

***
### 登录页
>django的admin登录页被我替换了，所以想要登录admin后台也是通过平台登录页来进入,页面比较渣有兴趣的同学可以帮忙设计下    
![login.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/login.png) 

***
### 仪表盘
>用来显示资产汇总、minion汇总等信息，统计信息  
![dashbord.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/dashboard.png)  

***
### 资源管理
>简单的cmdb功能，支持批量导入导出，通过下载模板把信息批量导入模板上传  
主机资源
![server_list.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/server_list.png)
导入功能
![server_list_manage](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/server_list_manage.png)
网络资源
![network_list](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/network_list.png)

***
### Minion管理
>通过后台定时采集minion数据入库，实时显示minion的情况，支持手动更新  
![minion_manage.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/minion_manage.png) 
minion详情  
![minion_info.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/minion_info.png)  

***
### SaleKey管理
>把saltkey命令搬到了平台里，方便直接操作minion的添加删除等  
![saltkey_manage.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/saltkey_manage.png)  

***
### Minion客户端部署
>salt-ssh远程部署minion客户端，调用的sls在`/src/salt/minion/init.sls`里,可以完成自动部署配置ID和启动等,sls内配置的是外网的yum源并且固定2017.7.5版本salt所以需要上网，如果有配置本地yum源可以自行修改    
![minion_client_install.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/minion_client_install.png)

***
### 模块部署
>执行部署各种自定义的sls，比如对客户机初始化，安装mysql、nginx、jdk等可以自己添加，自动化运维利器，可以批量部署
![minion_deploy.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/minion_develop.png)

***
### SSH模块部署
>这个功能页面暂时没有开发，不过和minion客户端安装是执行类似的代码，这是为了那些不允许安装salt客户端准备的页面

***
### Salt命令集
>自动收集salt命令，提供官方的使用帮助查看，自定义选择要收集的salt主机，因为windows和linux命令有不同  
![salt_cmd_manage.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/salt_cmd_manage.png)

***
### Salt命令执行
>强大的salt命令执行页面，直接把CLI的salt迁移到页面来，并且支持模块自动补全，命令自动补全，命令使用帮助自动加载  
![salt_cmd_exe.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/salt_cmd_exe.png)  
命令帮助
![salt_cmd_exe_help.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/salt_cmd_exe_help.png)  


***
### Salt工具
>sal命令的快捷通道，按需封装常用的salt命令，无限扩展，方便使用
![salt_tool.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/salt_tool.png)  

***
### 应用发布
>可以自定义新增发布，文件推送目前只支持使用svn，svn如果使用https第一次需要到CLI进行一次认证，功能非常个性化，可以按正常流程更新svn->停止应用->同步文件->启动应用，可以单独用来应用停止、启动、同步文件，可以支持对客户端执行命令等等
![app_release.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/app_release.png)  
![edit_app_release.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/edit_app_release.png)  


***
### 应用发布组
>创建应用组，添加成员，对应用进行分组，方便各自管理各自的应用，后期会添加用户权限管理
![app_group.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/app_group.png)  
![app_group_member.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/app_group_member.png)  

***
### 发布授权
>对登录用户进行权限控制，按需分配可执行的发布应用
![app_auth.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/app_auth.png)  

***
### 网络扫描
>网络嗅探小工具，可以扫描路由可达网段的在线IP和局域网内IP，可以扫描内外网IP的开放端口以及跟踪路由信息等  
![netscantool.png](https://github.com/xiaopanggege/xpgg_oms/raw/master/static/screenshot/netscantool.png)  
