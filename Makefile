.PHONY: setup dev clean build format lint test publish-test publish test-install

setup:
	uv venv
	uv pip install -e .

dev: setup
	uv pip install -e ".[dev]"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .uv-cache/
	rm -rf .venv/
	rm -rf test-install/

build: clean
	uv build --no-sources

# Development commands
.PHONY: format lint test

format:
	black .
	ruff --fix .

lint:
	black --check .
	ruff check .
	mypy src/minimax

test: dev
	pytest tests/ -v

# Publishing commands
publish-test: build test
	uv publish dist/* --publish-url https://test.pypi.org/legacy/

publish: build test
	uv publish dist/*

# Test installation from TestPyPI
test-install:
	rm -rf test-install
	mkdir -p test-install
	cd test-install && \
	python3 -m venv .venv && \
	. .venv/bin/activate && \
	pip install --index-url https://test.pypi.org/simple/ \
		--extra-index-url https://pypi.org/simple/ \
		minimax-python && \
	python3 -c "from minimax import Minimax; print('✨ Package successfully installed and imported!')" && \
	echo "🎉 Installation test complete! The package works correctly."
