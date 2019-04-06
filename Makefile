PREFIX ?= /usr/local

install:
	@cp epr.py epr
	@chmod +x epr
	@mv epr $(PREFIX)/bin/epr

uninstall:
	@rm $(PREFIX)/bin/epr

.PHONY: install uninstall
