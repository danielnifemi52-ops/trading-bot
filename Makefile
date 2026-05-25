# Makefile for project launcher

.PHONY: start test check build

start:
	cd backend && python start.py

check:
	cd backend && python check.py

test:
	cd backend && python -m pytest
