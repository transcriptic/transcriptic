import pytest
from transcriptic.config import AnalysisException
from .helpers.mockAPI import mockRoute


class TestAnalyze:
    @pytest.fixture(autouse=True)
    def init_db(self, json_db, response_db):
        # Load all the protocol and response json we may use for this test class
        json_db.load("invalidTransfer")
        json_db.load("invalidTransfer_response")
        json_db.load("singleTransfer")
        json_db.load("singleTransfer_response")

        # Load all our mock responses
        response_db.load(name="mock404", status_code=404, text="404")
        response_db.load(name="mock400", status_code=400, text="400")
        response_db.load(
            name="mock422", status_code=422, json=json_db["invalidTransfer_response"]
        )
        response_db.load(
            name="mock200", status_code=200, json=json_db["singleTransfer_response"]
        )

    def testDefaultResponses(self, test_api, json_db, response_db):
        # Setup default parameters for route mocking
        route = test_api.get_route("analyze_run")
        call = "post"

        mockRoute(call, route, response_db["mock404"], max_calls=1)
        with pytest.raises(Exception):
            test_api.analyze_run(json_db["invalidTransfer"])

        mockRoute(call, route, response_db["mock400"], max_calls=1)
        with pytest.raises(Exception):
            test_api.analyze_run(json_db["invalidTransfer"])

        mockRoute(call, route, response_db["mock422"], max_calls=1)
        with pytest.raises(AnalysisException):
            test_api.analyze_run(json_db["invalidTransfer"])

        mockRoute(call, route, response_db["mock200"], max_calls=1)
        assert (
            test_api.analyze_run(json_db["singleTransfer"])
            == json_db["singleTransfer_response"]
        )

    def testGetOrganizations(self, test_api, json_db, response_db):
        # Setup parameters for route mocking
        route = test_api.get_route("get_organizations")
        call = "get"

        mockRoute(call, route, response_db["mock404"], max_calls=1)
        with pytest.raises(Exception):
            test_api.organizations()

        mockRoute(call, route, response_db["mock200"], max_calls=1)
        assert test_api.organizations() == json_db["singleTransfer_response"]

    def testGetOrganization(self, test_api, json_db, response_db):
        # Setup parameters for route mocking
        route = test_api.get_route("get_organization", org_id="mock")
        call = "get"

        mockRoute(call, route, response_db["mock404"], max_calls=1)
        with pytest.raises(Exception):
            test_api.get_organization(org_id="mock")

        mockRoute(call, route, response_db["mock200"], max_calls=1)
        assert (test_api.get_organization(org_id="mock")).json() == json_db[
            "singleTransfer_response"
        ]
