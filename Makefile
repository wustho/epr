dev:
	poetry install

release:
	python -m build
	twine upload --skip-existing dist/*
