
import pytest
from src.parsers import parse_vmess_uri, parse_links
from src.models import Node


def test_parse_vmess_uri_valid():
    # A base64 encoded vmess link for testing
    # JSON: {"v": "2", "ps": "test-node", "add": "test.server.com", "port": "443", "id": "a-uuid-goes-here", "aid": "64", "net": "ws", "type": "none", "host": "test.server.com", "path": "/", "tls": "tls", "sni": "test.server.com"}
    valid_link = "vmess://eyJ2IjogIjIiLCAicHMiOiAidGVzdC1ub2RlIiwgImFkZCI6ICJ0ZXN0LnNlcnZlci5jb20iLCAicG9ydCI6ICI0NDMiLCAiaWQiOiAiYS11dWlkLWdvZXMtaGVyZSIsICJhaWQiOiAiNjQiLCAibmV0IjogIndzIiwgInR5cGUiOiAibm9uZSIsICJob3N0IjogInRlc3Quc2VydmVyLmNvbSIsICJwYXRoIjogIi8iLCAidGxzIjogInRscyIsICJzbmkiOiAidGVzdC5zZXJ2ZXIuY29tIn0="
    
    result = parse_vmess_uri(valid_link)
    
    assert result is not None
    assert result["protocol"] == "vmess"
    assert result["settings"]["vnext"][0]["address"] == "test.server.com"
    assert result["settings"]["vnext"][0]["port"] == 443
    assert result["settings"]["vnext"][0]["users"][0]["id"] == "a-uuid-goes-here"
    assert result["streamSettings"]["network"] == "ws"
    assert result["streamSettings"]["security"] == "tls"
    assert result["streamSettings"]["wsSettings"]["path"] == "/"
    assert result["streamSettings"]["wsSettings"]["headers"]["Host"] == "test.server.com"
    assert result["streamSettings"]["tlsSettings"]["serverName"] == "test.server.com"


def test_parse_vmess_uri_invalid():
    invalid_link = "vmess://invalid-base64"
    assert parse_vmess_uri(invalid_link) is None

    not_vmess_link = "http://google.com"
    assert parse_vmess_uri(not_vmess_link) is None


def test_parse_links():
    links = [
        "vmess://eyJ2IjogIjIiLCAicHMiOiAidGVzdC1ub2RlIiwgImFkZCI6ICJ0ZXN0LnNlcnZlci5jb20iLCAicG9ydCI6ICI0NDMiLCAiaWQiOiAiYS11dWlkLWdvZXMtaGVyZSIsICJhaWQiOiAiNjQiLCAibmV0IjogIndzIiwgInR5cGUiOiAibm9uZSIsICJob3N0IjogInRlc3Quc2VydmVyLmNvbSIsICJwYXRoIjogIi8iLCAidGxzIjogInRscyIsICJzbmkiOiAidGVzdC5zZXJ2ZXIuY29tIn0=",
        "invalid-link",
        ""
    ]
    
    nodes = parse_links(links)
    
    assert len(nodes) == 2
    assert isinstance(nodes[0], Node)
    assert nodes[0].config == links[0]
    assert isinstance(nodes[1], Node)
    assert nodes[1].config == links[1]
