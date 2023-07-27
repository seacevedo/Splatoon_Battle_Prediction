cd ./integration_files/

docker build -t splatoon-winner-prediction:v0 .
docker run -dp 127.0.0.1:9696:9696 --name integration-test splatoon-winner-prediction:v0
sleep 5
cd ..
python3 test_docker.py
docker stop integration-test
