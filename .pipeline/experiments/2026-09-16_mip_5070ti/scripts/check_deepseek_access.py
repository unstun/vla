"""One read-only request to the user-configured/default endpoint; no redirects.

Load the private server env file before invoking. Only sanitized status and
model identifiers are recorded; credentials and raw error responses are omitted.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    report = {"time_utc": datetime.now(timezone.utc).isoformat(),
              "method": "GET", "required_model": "deepseek-flash", "passed": False}
    if not key:
        report["error"] = "missing_credential"
    elif (parsed.scheme != "https" or not parsed.hostname or parsed.username
          or parsed.password or parsed.query or parsed.fragment):
        report["error"] = "unsupported_endpoint_configuration"
    else:
        report["endpoint"] = base + "/models"
        request = urllib.request.Request(report["endpoint"], headers={
            "Authorization": "Bearer " + key, "Accept": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
                report["http_status"] = response.status
                body = response.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise ValueError("oversized_response")
                data = json.loads(body)
                models = [item["id"] for item in data["data"]]
                if not all(isinstance(m, str) and re.fullmatch(r"[A-Za-z0-9._:/-]{1,128}", m)
                           and key not in m for m in models):
                    raise ValueError("invalid_model_identifiers")
                report["models"] = models
                report["passed"] = "deepseek-flash" in models
                if not report["passed"]:
                    report["error"] = "required_model_not_listed"
        except urllib.error.HTTPError as exc:
            report["http_status"] = exc.code
            report["error"] = ("authentication_rejected" if exc.code == 401 else
                               "redirect_refused" if 300 <= exc.code < 400 else "http_error")
        except (urllib.error.URLError, TimeoutError, OSError):
            report["error"] = "transport_error"
        except (ValueError, TypeError, KeyError):
            report["error"] = "invalid_models_response"
    path = Path(__file__).resolve().parents[1] / "setup" / (
        "api_access_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
