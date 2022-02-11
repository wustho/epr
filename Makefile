dev:
	poetry install --no-root

release:
	python setup.py sdist bdist_wheel
	twine upload --skip-existing dist/*
