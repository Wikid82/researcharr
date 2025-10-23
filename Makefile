.PHONY: docs-preview

# Serve the docs/ folder locally at http://localhost:8000
docs-preview:
	python3 -m http.server --directory docs 8000
