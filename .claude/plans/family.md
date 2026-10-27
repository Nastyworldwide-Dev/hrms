CLASS: a URL the page links under /hrms/ falls into the app catch-all route
hrms/hooks.py /hrms/manifest.webmanifest same-root — own rule before /hrms/<path:app_path>
hrms/hooks.py /hrms/sw.js not-affected — has its own rule since alpha.12
frontend/index.html apple-touch-icon / splash links not-affected — absolute /assets/hrms/manifest/ URLs, served as static files
