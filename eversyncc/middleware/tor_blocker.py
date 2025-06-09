import requests
from django.http import HttpResponse

def load_tor_exit_nodes():
    try:
        response = requests.get("https://check.torproject.org/torbulkexitlist")
        if response.status_code == 200:
            return set(response.text.strip().split("\n"))
    except Exception:
        pass
    return set()

TOR_EXIT_NODES = load_tor_exit_nodes()

def is_tor_ip(ip):
    return ip in TOR_EXIT_NODES

class BlockTorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')
        if ip and is_tor_ip(ip):
            return HttpResponse(
                "<html><body><h1>🐾 Access Denied</h1><p>We don’t allow connections from Tor exit nodes. Please try again without Tor. Love you!</p></body></html>",
                status=403
            )
        return self.get_response(request)