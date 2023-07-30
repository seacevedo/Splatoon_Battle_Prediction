
unit_testing:
	pytest unit_tests/

quality_checks:
	isort .
	black .
	pylint --recursive=y .

integration_testing: unit_testing quality_checks
	bash integration_tests/run.sh


setup_pipenv:
	sudo apt-get update -y
	sudo apt install python3-pip -y
	sudo pip install pipenv
	sudo python3 -m pipenv --python 3.10.6
	sudo python3 -m pipenv update
	sudo python3 -m pipenv shell

