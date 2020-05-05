import pytest as _pytest

import functions.manager as manager
from functions.manager import Boto3Error as Boto3Error
from functions.manager import Boto3Result as Boto3Result


class TestBoto3Result:
    def test_Boto3Result_with_body(self, result_with_body):
        assert result_with_body.status == "200"
        assert result_with_body.body == {
            "ResponseMetadata": {"HTTPStatusCode": "200"},
            "foo": "bar",
        }
        assert result_with_body.exc is None
        assert result_with_body.error == {}

    def test_Boto3Result_with_exception(
        self, result_with_exception, test_exception
    ):
        assert result_with_exception.status is None
        assert result_with_exception.body == {}
        assert isinstance(result_with_exception.exc, test_exception)
        assert isinstance(result_with_exception.error, dict)
        assert all(
            key in result_with_exception.error
            for key in ("title", "message", "traceback")
        )

    def test_Boto3Result_with_neither(self, inputerror_exception, boto3result):
        with _pytest.raises(inputerror_exception):
            boto3result()

    def test_Boto3Result_with_http_failure(self):
        result_with_http_failure = Boto3Result(
            response={
                "ResponseMetadata": {"HTTPStatusCode": "429"},
                "foo": "bar",
            }
        )
        assert result_with_http_failure.status == "429"
        assert result_with_http_failure.body == {
            "ResponseMetadata": {"HTTPStatusCode": "429"},
            "foo": "bar",
        }
        assert result_with_http_failure.exc is None
        assert result_with_http_failure.error == {
            "message": "http status was 429",
            "title": "HTTP status not OK.",
            "traceback": None,
        }


class TestInvoke:
    def test_invoke_body(self, mocker):
        mock_function = mocker.Mock(return_value={"somedict": "return_value"})
        params = {"foo": "foo_arg", "bar": "bar_arg", "baz": "baz_arg"}

        result = manager.invoke(mock_function, **params)

        mock_function.assert_called_once_with(**params)
        assert isinstance(result, Boto3Result)
        assert result.body == {"somedict": "return_value"}
        assert result.exc is None

    def test_invoke_exc(self, test_exception_raiser):
        result = manager.invoke(test_exception_raiser)

        assert isinstance(result, Boto3Result)
        assert result.body == {}
        assert isinstance(result.exc, Boto3Error)


class TestUpdateService:
    def test_update_service(self, mocker, fake_ecs_client):
        fake_invoke = mocker.patch.object(
            manager,
            "invoke",
            return_value=Boto3Result({"response": "a_response"}),
        )

        result = manager.update_service(
            ecs_client=fake_ecs_client,
            service_name="some_service_name",
            taskdef_id="some_taskdef_id",
            cluster_id="some_cluster",
        )

        assert isinstance(result, Boto3Result)
        assert isinstance(result.body, dict)
        assert result.exc is None

        fake_invoke.assert_called_once_with(
            fake_ecs_client.update_service,
            **{
                "service": "some_service_name",
                "cluster": "some_cluster",
                "taskDefinition": "some_taskdef_id",
                "forceNewDeployment": False,
            },
        )

    def test_update_service_exc(
        self, mocker, fake_ecs_client, result_with_exception
    ):
        fake_invoke = mocker.patch.object(
            manager, "invoke", return_value=result_with_exception
        )

        result = manager.update_service(
            ecs_client=fake_ecs_client,
            service_name="some_service_name",
            cluster_id="some_cluster",
        )

        fake_invoke.assert_called_once()
        assert isinstance(result, Boto3Result)
        assert isinstance(result.body, dict)
        assert result.body == {}
        assert isinstance(result.exc, Exception)