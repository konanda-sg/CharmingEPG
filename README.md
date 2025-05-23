# CharmingEPG

## Support

- MyTV Super
- NowTV(需要配置NOWTV_CHANNEL_FILTER)
- Hami

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
  -e NOWTV_CHANNEL_NO_FILTER='[96,99,102,105,108,111,112,113,114,115,116,150,155,156,162,200,321,325,328,329,330,331,332,333,366,367,371,538,540,541,542,543,545,548,551,552,553,555,561,611,612,613,621,622,623,624,625,626,627,630,631,632,633,634,635,636,637,638,639,643,644,645,646,680,683,684]' \
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