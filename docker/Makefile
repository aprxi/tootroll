
NAME := tootroll

HTTP_PORT_BACKEND := 8888
HTTP_PORT_FRONTEND := 8080


export NAME
export HTTP_PORT

.PHONY: app
app:
	docker compose up --build -d
	@echo "Login at http://localhost:${HTTP_PORT_FRONTEND}"

.PHONY: rebuild
rebuild: clean app

.PHONY: clean
clean:
	docker compose down -v
