.PHONY: help install install-python install-npm build minify minify-css minify-js security security-python security-npm pip-audit safety bandit npm-audit copy-deps clean

# Default target
help:
	@echo "Radio Calico - Available Make Targets"
	@echo ""
	@echo "Installation:"
	@echo "  make install         - Install all dependencies (Python + npm)"
	@echo "  make install-python  - Install Python dependencies"
	@echo "  make install-npm     - Install npm dependencies and copy to static"
	@echo ""
	@echo "Build:"
	@echo "  make build           - Build and minify all assets (CSS + JS)"
	@echo "  make minify          - Minify CSS and JavaScript files"
	@echo "  make minify-css      - Minify only CSS files"
	@echo "  make minify-js       - Minify only JavaScript files"
	@echo ""
	@echo "Security Scanning:"
	@echo "  make security        - Run all security scans (Python + npm)"
	@echo "  make security-python - Run all Python security scans"
	@echo "  make security-npm    - Run npm audit"
	@echo "  make pip-audit       - Scan Python dependencies with pip-audit"
	@echo "  make safety          - Scan Python dependencies with safety"
	@echo "  make bandit          - Scan Python code for security issues"
	@echo "  make npm-audit       - Run npm security audit"
	@echo ""
	@echo "Utilities:"
	@echo "  make copy-deps       - Copy npm dependencies to static directory"
	@echo "  make clean           - Remove generated files and dependencies"

# Install all dependencies
install: install-python install-npm

# Install Python dependencies
install-python:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

# Install npm dependencies and copy to static
install-npm:
	@echo "Installing npm dependencies..."
	npm install
	@$(MAKE) copy-deps

# Copy npm dependencies to static directory
copy-deps:
	@echo "Copying hls.js to static/js directory..."
	@mkdir -p static/js
	@cp node_modules/hls.js/dist/hls.min.js static/js/
	@cp node_modules/hls.js/dist/hls.min.js.map static/js/ 2>/dev/null || true
	@echo "Dependencies copied successfully"

# Build and minify all assets
build: minify
	@echo "Build complete!"

# Minify CSS and JavaScript
minify: minify-css minify-js
	@echo "Minification complete!"

# Minify CSS files
minify-css:
	@echo "Minifying CSS..."
	@npx csso static/style.css -o static/style.min.css
	@echo "CSS minified: style.css → style.min.css"

# Minify JavaScript files
minify-js:
	@echo "Minifying JavaScript..."
	@npx terser static/script.js -o static/script.min.js -c -m
	@echo "JavaScript minified: script.js → script.min.js"

# Run all security scans
security: security-python security-npm
	@echo ""
	@echo "========================================="
	@echo "All security scans completed!"
	@echo "========================================="

# Run all Python security scans
security-python: pip-audit safety bandit
	@echo ""
	@echo "Python security scans completed"

# Run npm security audit
security-npm: npm-audit
	@echo ""
	@echo "npm security scan completed"

# Scan Python dependencies with pip-audit
pip-audit:
	@echo "Running pip-audit..."
	@if [ -f venv/bin/pip-audit ]; then \
		venv/bin/pip-audit --desc || true; \
	else \
		pip-audit --desc || true; \
	fi

# Scan Python dependencies with safety
safety:
	@echo ""
	@echo "Running safety..."
	@if [ -f venv/bin/safety ]; then \
		venv/bin/safety check --json || true; \
	else \
		safety check --json || true; \
	fi

# Scan Python code for security issues with bandit
bandit:
	@echo ""
	@echo "Running bandit..."
	@if [ -f venv/bin/bandit ]; then \
		venv/bin/bandit -r . -f json -o bandit-report.json --exclude ./venv,./node_modules 2>/dev/null || true; \
		venv/bin/bandit -r . --exclude ./venv,./node_modules || true; \
	else \
		bandit -r . -f json -o bandit-report.json --exclude ./venv,./node_modules 2>/dev/null || true; \
		bandit -r . --exclude ./venv,./node_modules || true; \
	fi

# Run npm audit
npm-audit:
	@echo "Running npm audit..."
	@npm audit --audit-level=moderate || true

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -rf node_modules
	@rm -rf static/js
	@rm -f bandit-report.json
	@rm -f package-lock.json
	@echo "Clean complete"
