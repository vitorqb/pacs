.PHONY: requirements


requirements:
	pip install -r requirements/base_frozen.txt

requirements/dev: requirements
	pip install -r requirements/development.txt

requirements/deploy:
	pip install -r requirements/deploy.txt
