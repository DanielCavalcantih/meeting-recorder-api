run:
	uvicorn main:app --reload

install:
	pip install -r requirements.txt

dev:
	uvicorn main:app --reload --port 8000

format:
	black .

lint:
	ruff .

start:
	python main.py