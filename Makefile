init:
	pip3 install -r requirements.txt

init-dev: init
	pip3 install -r requirements-dev.txt

test:
	py.test -s --tb=native .

dist: 
	rm -rf dist
	pip3 install --user --upgrade setuptools wheel
	python3 setup.py sdist bdist_wheel
	
.PHONY: init init-dev test dist