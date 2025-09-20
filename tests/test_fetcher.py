import pytest
from aiohttp import web
from src.fetcher import SubscriptionFetcher


@pytest.fixture
def app():
    """Creates a mock aiohttp app for testing."""
    app = web.Application()

    async def source1(request):
        return web.Response(text="config1\nconfig2")

    async def source2(request):
        return web.Response(text="config3\nconfig1")

    async def bad_source(request):
        raise web.HTTPInternalServerError()

    async def base64_source(request):
        # base64 encoding of "decoded-config1\ndecoded-config2"
        encoded_content = "ZGVjb2RlZC1jb25maWcxCmRlY29kZWQtY29uZmlnMg=="
        return web.Response(text=encoded_content)

    app.router.add_get("/source1", source1)
    app.router.add_get("/source2", source2)
    app.router.add_get("/bad_source", bad_source)
    app.router.add_get("/base64_source", base64_source)

    return app


@pytest.mark.asyncio
async def test_fetch_all_success(aiohttp_client, app):
    """Test that fetch_all successfully fetches from multiple sources."""
    client = await aiohttp_client(app)
    sources = [str(client.make_url("/source1")), str(client.make_url("/source2"))]
    fetcher = SubscriptionFetcher(sources)

    configs = await fetcher.fetch_all()

    assert len(configs) == 3
    assert "config1" in configs
    assert "config2" in configs
    assert "config3" in configs


@pytest.mark.asyncio
async def test_fetch_all_with_failures(aiohttp_client, app):
    """Test that fetch_all handles failed requests gracefully."""
    client = await aiohttp_client(app)
    sources = [str(client.make_url("/source1")), str(client.make_url("/bad_source"))]
    fetcher = SubscriptionFetcher(sources)

    configs = await fetcher.fetch_all()

    assert len(configs) == 2
    assert "config1" in configs
    assert "config2" in configs


@pytest.mark.asyncio
async def test_fetch_all_base64_decoding(aiohttp_client, app):
    """Test that fetch_all correctly decodes base64 content."""
    client = await aiohttp_client(app)
    sources = [str(client.make_url("/base64_source"))]
    fetcher = SubscriptionFetcher(sources)

    configs = await fetcher.fetch_all()

    assert len(configs) == 2
    assert "decoded-config1" in configs
    assert "decoded-config2" in configs