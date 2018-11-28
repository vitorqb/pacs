.PHONY: requirements


requirements:
	pip install -r requirements/base.txt

requirements/dev: requirements
	pip install -r requirements/development.txt
