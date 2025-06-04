# CharmingEPG

## Support

- MyTV Super
- NowTV
- Hami
- Astro Go（中文台都是中文描述）
- CN (via epg.pw)

## Feature
- 获取多个平台的7天EPG，每天更新一次。
- 每天生成的epg以xml存在本地。
- 如需持久化epg文件，请挂载/code/epg_files目录。

## How to use


### 配置需要启用的平台

```dotenv
EPG_ENABLE_CN=true
EPG_ENABLE_TVB=true
EPG_ENABLE_NOWTV=false
EPG_ENABLE_HAMI=true
EPG_ENABLE_ASTRO=false
```

支持`1`/`0` `yes`/`no` `true`/`false` `on`/`off`
这些配置已经在`docker-compose.example.yml`中列好，自行配置即可。

### Docker Compose

```bash
cp docker-compose.example.yml docker-compose.yml
#然后修改docker-compose.yml
#.....

#部署并运行
docker-compose build && docker-compose up -d
```

### Docker Cli

```bash
# 自行配置平台开关
docker run -d \
  -p 30008:80 \
  --name charming_epg \
  -e EPG_ENABLE_CN=true \
  -e EPG_ENABLE_TVB=true \
  -e EPG_ENABLE_NOWTV=false \
  -e EPG_ENABLE_HAMI=true \
  -e EPG_ENABLE_ASTRO=false \
  $(docker build -q .)
```

### Request

#### 请求所有平台

```
http://[ip]:[port]/all
```

#### 请求单个或多个平台

```
http://[ip]:[port]/epg?platforms=tvb,nowtv,hami,astro,cn
```