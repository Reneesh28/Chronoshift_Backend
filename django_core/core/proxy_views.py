import os
import httpx
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

SIMULATOR_URL = os.getenv("SIMULATOR_URL")
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL")

if not SIMULATOR_URL:
    raise ValueError("SIMULATOR_URL environment variable is missing. Configure it in your .env or the system context.")
if not AI_ENGINE_URL:
    raise ValueError("AI_ENGINE_URL environment variable is missing. Configure it in your .env or the system context.")

@csrf_exempt
def proxy_to_simulator(request, path=""):
    """
    Proxies REST requests dynamically to the FastAPI Simulator.
    """
    url = f"{SIMULATOR_URL}/{path}" if path else SIMULATOR_URL
    return _proxy_request(request, url)

@csrf_exempt
def proxy_to_ai_engine(request, path=""):
    """
    Proxies REST requests dynamically to the Flask AI Engine.
    """
    url = f"{AI_ENGINE_URL}/{path}" if path else AI_ENGINE_URL
    return _proxy_request(request, url)

def _proxy_request(request, url):
    # Construct proxy headers (filtering host & content-length to avoid issues)
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ["host", "content-length"]:
            headers[k] = v

    # Forward query parameters
    params = request.GET.dict()

    # Forward the binary body content
    content = request.body

    try:
        # Use httpx to make a synchronous request mirroring the client request
        with httpx.Client() as client:
            resp = client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=params,
                content=content,
                timeout=60.0
            )

            # Build standard Django HttpResponse
            response = HttpResponse(
                content=resp.content,
                status=resp.status_code,
                content_type=resp.headers.get("content-type")
            )

            # Mirror safe headers back to the client
            for k, v in resp.headers.items():
                if k.lower() not in ["transfer-encoding", "content-encoding", "content-length", "connection"]:
                    response[k] = v

            return response

    except httpx.RequestError as e:
        return HttpResponse(
            content=f"ChronoShift Monolith Proxy Error: {str(e)}",
            status=502,
            content_type="text/plain"
        )
