
unit_testing:
	pytest unit_tests/

quality_checks:
	isort .
	black .
	pylint --recursive=y .

integration_testing: unit_testing quality_checks
	bash integration_tests/run.sh


setup:
	sudo apt-get update -y
	sudo apt install python3-pip -y
	sudo pip install pipenv
	sudo python3 -m pipenv --python 3.10.6
	sudo python3 -m pipenv update
	sudo python3 -m pipenv shell
	sudo apt-get install ca-certificates curl gnupg
	sudo install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
	sudo chmod a+r /etc/apt/keyrings/docker.gpg
	echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
	sudo apt-get update -y
	sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
	sudo apt install docker-compose -y
	cd monitoring
	sudo docker-compose -f docker_compose.yaml up -d
	cd ..
	wandb login
	cd flows
