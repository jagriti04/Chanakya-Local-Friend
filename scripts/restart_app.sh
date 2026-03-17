docker stop chanakya
docker rm chanakya
docker build -t chanakya-assistant .
docker run --restart=always -d --network="host" --env-file .env --name chanakya chanakya-assistant
