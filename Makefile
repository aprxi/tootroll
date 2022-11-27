NAME := tootroll

RUN := poetry run


.PHONY: pre-commit
pre-commit:
	$(RUN) pre-commit run --all-files

.PHONY: install
install: clean
	poetry build
	python -m pip install --force-reinstall dist/$(NAME)-*.whl

.PHONY: docker
docker:
	docker build -t $(NAME):latest .

.PHONY: remove_docker
remove_docker:
	docker rm -f `docker ps -qaf name=$(NAME)` 2>/dev/null || exit 0

.PHONY: run
run: remove_docker
	docker run -d \
		--name $(NAME) \
		-p 8888:8888 \
		--rm $(NAME):latest

.PHONY: clean
clean:
	[ -d ./dist ] && rm -rf ./dist || exit 0
	[ -d ./.mypy_cache ] && rm -rf ./.mypy_cache || exit 0
	[ -d ./.cache ] && rm -rf ./.cache || exit 0
	[ -d ./build ] && rm -rf ./build || exit 0
	find ./ -type f -name '*.pyc' -delete -o -type d -name __pycache__ -delete
