"""Unit tests for Exa AI-powered semantic job discovery.

The Exa client is mocked entirely — no network, no ``exa_py`` install required.
``search_jobs`` runs the (mocked) blocking client in a thread executor, so these
exercise the real async path while keeping the client a fake.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.automation.platforms.base import JobListing
from app.core.job_discovery.exa_search import (
    DEFAULT_NUM_RESULTS,
    ExaJobSearch,
)


def _result(
    *,
    id="exa-1",
    title="Senior Python Developer at Acme",
    url="https://acme.example.com/jobs/1",
    text="We are hiring. This role is fully remote. Location: San Francisco, CA",
):
    """A duck-typed Exa search result item."""
    return SimpleNamespace(id=id, title=title, url=url, text=text)


def _results(items):
    """A duck-typed Exa search-and-contents response (has ``.results``)."""
    return SimpleNamespace(results=items)


# ---------------------------------------------------------------------------
# .available
# ---------------------------------------------------------------------------


class TestAvailable:
    def test_false_without_api_key(self):
        # No key short-circuits before any import attempt.
        assert ExaJobSearch(api_key="").available is False

    def test_false_when_empty_string_default(self):
        assert ExaJobSearch().available is False

    def test_true_with_key_when_exa_importable(self):
        search = ExaJobSearch(api_key="sk-test")
        # Stand in for the optional exa_py dependency so the test does not
        # depend on whether it is installed in the environment.
        with patch.dict("sys.modules", {"exa_py": MagicMock()}):
            assert search.available is True

    def test_false_with_key_when_exa_not_installed(self):
        import builtins

        search = ExaJobSearch(api_key="sk-test")
        real_import = builtins.__import__

        def _boom(name, *args, **kwargs):
            if name == "exa_py":
                raise ImportError("no exa_py")
            return real_import(name, *args, **kwargs)

        # Has a key, but the optional dependency import fails => unavailable.
        with patch("builtins.__import__", side_effect=_boom):
            assert search.available is False


# ---------------------------------------------------------------------------
# _build_query
# ---------------------------------------------------------------------------


class TestBuildQuery:
    def test_minimal_query_only(self):
        q = ExaJobSearch()._build_query("python developer", "", "")
        assert q == "hiring python developer job posting application"

    def test_includes_location(self):
        q = ExaJobSearch()._build_query("data scientist", "Berlin", "")
        assert q == "hiring data scientist in Berlin job posting application"

    def test_includes_job_type(self):
        q = ExaJobSearch()._build_query("ML engineer", "", "contract")
        assert q == "hiring ML engineer contract position job posting application"

    def test_full_ordering_location_then_type(self):
        q = ExaJobSearch()._build_query("SRE", "Remote", "full-time")
        # Order must be: hiring <q>, in <loc>, <type> position, trailer.
        assert q == "hiring SRE in Remote full-time position job posting application"

    def test_empty_strings_are_omitted_not_blank(self):
        q = ExaJobSearch()._build_query("dev", "", "")
        assert "  " not in q  # no double spaces from empty optional parts
        assert q.startswith("hiring dev")
        assert q.endswith("job posting application")


# ---------------------------------------------------------------------------
# _parse_results
# ---------------------------------------------------------------------------


class TestParseResults:
    def test_maps_to_joblisting_with_exa_platform(self):
        listings = ExaJobSearch()._parse_results(_results([_result()]))
        assert len(listings) == 1
        job = listings[0]
        assert isinstance(job, JobListing)
        assert job.platform == "exa"
        assert job.title == "Senior Python Developer at Acme"
        assert job.url == "https://acme.example.com/jobs/1"

    def test_company_extracted_from_at_pattern(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(title="Backend Engineer at Globex")])
        )
        assert listings[0].company == "Globex"

    def test_company_extracted_from_dash_pattern(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(title="Backend Engineer - Initech")])
        )
        assert listings[0].company == "Initech"

    def test_company_falls_back_to_domain(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(title="Backend Engineer", url="https://www.umbrella.com/x")])
        )
        # www. stripped, first domain label title-cased.
        assert listings[0].company == "Umbrella"

    def test_company_unknown_when_no_title_and_no_url(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(title="JustATitle", url="")])
        )
        assert listings[0].company == "Unknown"

    def test_remote_detected_from_text(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(text="This is a fully remote role.")])
        )
        assert listings[0].remote is True

    def test_remote_false_when_no_signal(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(text="Onsite only, must relocate to the office daily.")])
        )
        assert listings[0].remote is False

    def test_location_extracted_from_text(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(text="Location: San Francisco, CA. Great team.")])
        )
        assert "San Francisco" in listings[0].location

    def test_platform_job_id_uses_id_when_present(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(id="abc123", url="https://x/1")])
        )
        assert listings[0].platform_job_id == "abc123"

    def test_platform_job_id_falls_back_to_url_when_id_falsy(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(id="", url="https://x/fallback")])
        )
        assert listings[0].platform_job_id == "https://x/fallback"

    def test_description_truncated_to_3000_chars(self):
        listings = ExaJobSearch()._parse_results(
            _results([_result(text="x" * 5000)])
        )
        assert len(listings[0].description) == 3000

    def test_handles_none_title_and_url(self):
        # r.title / r.url may be None; module coerces with ``or ""``.
        listings = ExaJobSearch()._parse_results(
            _results([_result(id="id-none", title=None, url=None, text="hello")])
        )
        job = listings[0]
        assert job.title == ""
        assert job.url == ""
        assert job.platform_job_id == "id-none"

    def test_missing_text_attribute_is_safe(self):
        # getattr(r, "text", "") path — item without a text attribute at all.
        item = SimpleNamespace(id="i", title="Role at Co", url="https://co/1")
        listings = ExaJobSearch()._parse_results(_results([item]))
        assert listings[0].description == ""
        assert listings[0].remote is False

    def test_empty_results_returns_empty_list(self):
        assert ExaJobSearch()._parse_results(_results([])) == []

    def test_multiple_results_preserve_order(self):
        listings = ExaJobSearch()._parse_results(
            _results(
                [
                    _result(id="1", title="A at One"),
                    _result(id="2", title="B at Two"),
                    _result(id="3", title="C at Three"),
                ]
            )
        )
        assert [j.platform_job_id for j in listings] == ["1", "2", "3"]
        assert [j.company for j in listings] == ["One", "Two", "Three"]


# ---------------------------------------------------------------------------
# search_jobs
# ---------------------------------------------------------------------------


class TestSearchJobs:
    async def test_returns_empty_when_not_available(self):
        # No key => not available => no client touched, empty result.
        search = ExaJobSearch(api_key="")
        result = await search.search_jobs("python developer")
        assert result == []

    async def test_never_calls_client_when_unavailable(self):
        search = ExaJobSearch(api_key="")
        with patch.object(ExaJobSearch, "_get_client") as get_client:
            result = await search.search_jobs("python developer")
        assert result == []
        get_client.assert_not_called()

    async def test_success_returns_parsed_listings(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.search_and_contents.return_value = _results(
            [_result(id="j1", title="Senior Dev at Acme")]
        )

        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(search, "_get_client", return_value=fake_client),
        ):
            listings = await search.search_jobs("python dev", location="NYC")

        assert len(listings) == 1
        assert listings[0].platform == "exa"
        assert listings[0].company == "Acme"
        # The composed semantic query was passed to the client.
        called_query = fake_client.search_and_contents.call_args.args[0]
        assert called_query == "hiring python dev in NYC job posting application"

    async def test_passes_num_results_through(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.search_and_contents.return_value = _results([])

        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(search, "_get_client", return_value=fake_client),
        ):
            await search.search_jobs("dev", num_results=7)

        kwargs = fake_client.search_and_contents.call_args.kwargs
        assert kwargs["num_results"] == 7

    async def test_default_num_results_used(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.search_and_contents.return_value = _results([])

        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(search, "_get_client", return_value=fake_client),
        ):
            await search.search_jobs("dev")

        kwargs = fake_client.search_and_contents.call_args.kwargs
        assert kwargs["num_results"] == DEFAULT_NUM_RESULTS

    async def test_empty_results_returns_empty_list(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.search_and_contents.return_value = _results([])

        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(search, "_get_client", return_value=fake_client),
        ):
            listings = await search.search_jobs("nothing matches")

        assert listings == []

    async def test_client_exception_is_swallowed_and_returns_empty(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.search_and_contents.side_effect = RuntimeError("exa boom")

        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(search, "_get_client", return_value=fake_client),
        ):
            listings = await search.search_jobs("python dev")

        # Errors must be caught: graceful empty list, no propagation.
        assert listings == []

    async def test_get_client_error_is_swallowed(self):
        # If client construction itself raises, search_jobs still returns [].
        search = ExaJobSearch(api_key="sk-test")
        with (
            patch.object(ExaJobSearch, "available", property(lambda self: True)),
            patch.object(
                search, "_get_client", side_effect=RuntimeError("no exa_py")
            ),
        ):
            listings = await search.search_jobs("python dev")

        assert listings == []


# ---------------------------------------------------------------------------
# _get_client error path (no key)
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_raises_without_api_key(self):
        search = ExaJobSearch(api_key="")
        with pytest.raises(RuntimeError, match="Exa API key not configured"):
            search._get_client()

    def test_constructs_and_caches_client_with_key(self):
        search = ExaJobSearch(api_key="sk-test")
        fake_exa_cls = MagicMock(return_value="CLIENT")
        fake_module = MagicMock(Exa=fake_exa_cls)

        with patch.dict("sys.modules", {"exa_py": fake_module}):
            first = search._get_client()
            second = search._get_client()

        assert first == "CLIENT"
        assert second is first  # cached: constructed only once
        fake_exa_cls.assert_called_once_with(api_key="sk-test")
