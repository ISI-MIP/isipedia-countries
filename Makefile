nb: venv
	venv/bin/jupyter notebook

venv: requirements.txt
	if [ ! -d "venv" ]; then python3 -m virtualenv venv; fi
	venv/bin/pip install -r requirements.txt
