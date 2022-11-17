NAME := tootroll

RUN := poetry run


.PHONY: pre-commit
pre-commit:
	$(RUN) pre-commit run --all-files

.PHONY: install
install: clean
	poetry build
	python -m pip install --force-reinstall dist/$(NAME)-*.whl

.PHONY: clean
clean:
	[ -d ./dist ] && rm -rf ./dist || exit 0
	[ -d ./.mypy_cache ] && rm -rf ./.mypy_cache || exit 0
	[ -d ./.cache ] && rm -rf ./.cache || exit 0
	[ -d ./build ] && rm -rf ./build || exit 0
	find ./ -type f -name '*.pyc' -delete -o -type d -name __pycache__ -delete
