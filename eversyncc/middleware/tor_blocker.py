import requests
from django.http import HttpResponse
import ipaddress
import time

class BlockTorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.tor_ips = set()
        self.last_refresh = 0
        self.refresh_interval = 600
        self.fetch_tor_exit_nodes()  

    def __call__(self, request):
        current_time = time.time()
        if current_time - self.last_refresh > self.refresh_interval:
            self.tor_ips = self.fetch_tor_exit_nodes()
            self.last_refresh = current_time

        ip_list = self.get_client_ips(request)
        normalized_ips = [self.normalize_ip(ip) for ip in ip_list]

        for ip in normalized_ips:
            if ip in self.tor_ips:
                return HttpResponse(
                    "<html><body><h1>Access Denied</h1><p>You're accessing from a Tor exit node. No onions here.</p></body></html>",
                    status=403
                )

        return self.get_response(request)

    def fetch_tor_exit_nodes(self):
        try:
            print("Fetching Tor exit node list...")
            response = requests.get("https://www.dan.me.uk/torlist/")
            if response.status_code == 200:
                raw_ips = response.text.strip().splitlines()
                nodes = set(str(ipaddress.ip_address(ip.strip())) for ip in raw_ips)
                print(f"Loaded {len(nodes)} normalized Tor exit IPs")
                return nodes
        except Exception as e:
            print(f"Error fetching Tor list: {e}")
        return set()

    def get_client_ips(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return [ip.strip() for ip in forwarded.split(",")]
        return [request.META.get("REMOTE_ADDR", "")]

    def normalize_ip(self, ip):
        try:
            return str(ipaddress.ip_address(ip))
        except ValueError:
            return ip