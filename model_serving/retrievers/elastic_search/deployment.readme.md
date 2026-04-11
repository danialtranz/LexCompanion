docker run -d \
--name es-server-lex-companion \
--network elastic-net \
--restart always \
-p 6504:9200 \
-e "discovery.type=single-node" \
-e "xpack.security.enabled=true" \
-e "xpack.security.http.ssl.enabled=false" \
-e "xpack.security.transport.ssl.enabled=false" \
-e "ELASTIC_PASSWORD=123456" \
-e "ES_JAVA_OPTS=-Xms2g -Xmx2g" \
-v $(pwd)/esdata:/usr/share/elasticsearch/data \
docker.elastic.co/elasticsearch/elasticsearch:8.13.0

docker run -d \
--name kibana-ui-lex-companion \
--network elastic-net \
--restart always \
-p 5601:5601 \
-e "ELASTICSEARCH_HOSTS=http://es-server-lex-companion:9200" \
-e "ELASTICSEARCH_SERVICEACCOUNTTOKEN=AAEAAWVsYXN0aWMva2liYW5hL2tpYmFuYS10b2tlbjpMLWxJZUtfcVFPT3M1Zm4wNHNaenZR" \
docker.elastic.co/kibana/kibana:8.13.0

SERVICE_TOKEN elastic/kibana/kibana-token = AAEAAWVsYXN0aWMva2liYW5hL2tpYmFuYS10b2tlbjpMLWxJZUtfcVFPT3M1Zm4wNHNaenZR

### tao netword

docker network create elastic-net

### tao token cho elastic search

docker exec -it es-server-lex-companion \
bin/elasticsearch-service-tokens create elastic/kibana kibana-token
