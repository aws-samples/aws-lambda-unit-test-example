checkOSDependencies:
	python3 --version | grep -q 3\.9 || (echo "Error: Requires Python 3.9" && exit 1)

createEnv: checkOSDependencies
	pip3 install virtualenv
	python3 -m venv venv
	source ./venv/bin/activate && pip3 install -r tests/requirements.txt

coverage:
	coverage run -m unittest discover
	coverage html --omit "tests/*",".venv/*"

unittest:
	pytest --disable-socket tests/unit/src/test_sampleLambda.py -s tests/unit/src/

deploy:
	sam build
	sam deploy --guided

scan:
	cfn_nag_scan --input-path template.yaml
	bandit src/sampleLambda/*.py tests/unit/src/*.py
