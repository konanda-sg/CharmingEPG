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
docker run -d \
  -p 30008:80 \
  --name charming_epg \
  $(docker build -q .)
```

### Request

#### 请求所有平台

```
http://[ip]:[port]/all
```

#### 请求单个或多个平台

```
http://[ip]:[port]/epg?platforms=tvb,nowtv,hami
```