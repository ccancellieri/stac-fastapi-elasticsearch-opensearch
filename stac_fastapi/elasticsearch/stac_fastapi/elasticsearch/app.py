"""FastAPI application."""

import os

from fastapi import APIRouter, FastAPI

from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.core.core import (
    AsyncCollectionSearchClient,
    BulkTransactionsClient,
    CoreClient,
    EsAsyncBaseFiltersClient,
    TransactionsClient,
)
from stac_fastapi.core.extensions import CollectionSearchPostExtension, QueryExtension
from stac_fastapi.core.extensions.aggregation import (
    EsAggregationExtensionGetRequest,
    EsAggregationExtensionPostRequest,
    EsAsyncAggregationClient,
)
from stac_fastapi.core.extensions.fields import FieldsExtension
from stac_fastapi.core.models import CollectionSearchPostRequest
from stac_fastapi.core.rate_limit import setup_rate_limit
from stac_fastapi.core.route_dependencies import get_route_dependencies
from stac_fastapi.core.session import Session
from stac_fastapi.elasticsearch.config import ElasticsearchSettings
from stac_fastapi.elasticsearch.database_logic import (
    DatabaseLogic,
    create_collection_index,
    create_index_templates,
)
from stac_fastapi.extensions.core import (  # CollectionSearchExtension,; CollectionSearchPostExtension
    AggregationExtension,
    FilterExtension,
    FreeTextExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension

# settings.openapi_url = "/app" # Not so sure what it exactly does, we need to fix links/base_url in the responses


# main_app = FastAPI(root_path="/main_app", redirect_slashes=False)
# api = StacApi(
#     title=os.getenv("STAC_FASTAPI_TITLE", "stac-fastapi-elasticsearch"),
#     description=os.getenv("STAC_FASTAPI_DESCRIPTION", "stac-fastapi-elasticsearch"),
#     api_version=os.getenv("STAC_FASTAPI_VERSION", "2.1"),
#     settings=settings,
#     extensions=extensions,
#     client=CoreClient(
#         database=database_logic, session=session, post_request_model=post_request_model
#     ),
#     search_get_request_model=create_get_request_model(search_extensions),
#     search_post_request_model=post_request_model,
#     route_dependencies=get_route_dependencies(),
#     app=main_app,
# )
# app = api.app


settings = ElasticsearchSettings()
session = Session.create_from_settings(settings)

filter_extension = FilterExtension(client=EsAsyncBaseFiltersClient())
filter_extension.conformance_classes.append(
    "http://www.opengis.net/spec/cql2/1.0/conf/advanced-comparison-operators"
)

database_logic = DatabaseLogic()

aggregation_extension = AggregationExtension(
    client=EsAsyncAggregationClient(
        database=database_logic, session=session, settings=settings
    )
)
aggregation_extension.POST = EsAggregationExtensionPostRequest
aggregation_extension.GET = EsAggregationExtensionGetRequest

collection_client = AsyncCollectionSearchClient(database=database_logic)

# main_app_router = APIRouter(prefix='/another_app')

search_extensions = [
    CollectionSearchPostExtension(
        POST=CollectionSearchPostRequest, client=collection_client, settings=settings
    ),
    TransactionExtension(
        client=TransactionsClient(
            database=database_logic, session=session, settings=settings
        ),
        settings=settings,
        # router=main_app_router
    ),
    BulkTransactionExtension(
        client=BulkTransactionsClient(
            database=database_logic,
            session=session,
            settings=settings,
        )
    ),
    FieldsExtension(),
    QueryExtension(),
    SortExtension(),
    TokenPaginationExtension(),
    filter_extension,
    FreeTextExtension(),
]

extensions = [aggregation_extension] + search_extensions

database_logic.extensions = [type(ext).__name__ for ext in extensions]

post_request_model = create_post_request_model(search_extensions)


root_path = os.getenv("STAC_FASTAPI_ROOT_PATH", "")
# root_path = f"{root_path}"

title = (os.getenv("STAC_FASTAPI_TITLE", "stac-fastapi-elasticsearch"),)
description = (os.getenv("STAC_FASTAPI_DESCRIPTION", "stac-fastapi-elasticsearch"),)
api_version = (os.getenv("STAC_FASTAPI_VERSION", "2.1"),)
app = FastAPI(
    title=title,
    description=description,
    api_version=api_version,
    root_path=root_path,
    redirect_slashes=True,
)

# api = StacApi(
#     title=f"{title}",
#     description=description,
#     api_version=api_version,
#     settings=settings,
#     extensions=extensions,
#     client=CoreClient(
#         database=database_logic, session=session, post_request_model=post_request_model
#     ),
#     search_get_request_model=create_get_request_model(search_extensions),
#     search_post_request_model=post_request_model,
#     route_dependencies=get_route_dependencies(),
#     app=app,
#     # router=app.router
# )
app.state.router_prefix = f"{root_path}"

catalogs = ["catalog_1", "catalog_2", "catalog_3"]
for catalog in catalogs:
    # root_path = f"/{catalog}"
    # router = APIRouter(prefix=f"{root_path}/catalogs/{catalog}")
    catalog_app = FastAPI(
        root_path=f"{root_path}/catalogs/{catalog}",
        openapi_prefix=f"{root_path}/catalogs/{catalog}",
        redirect_slashes=True,
    )

    # catalog_app.state.router_prefix=f"{root_path}/catalogs/{catalog}"

    api = StacApi(
        title=f"{title} - {catalog}",
        description=description,
        api_version=api_version,
        settings=settings,
        extensions=extensions,
        client=CoreClient(
            database=database_logic,
            session=session,
            post_request_model=post_request_model,
        ),
        search_get_request_model=create_get_request_model(search_extensions),
        search_post_request_model=post_request_model,
        route_dependencies=get_route_dependencies(),
        app=catalog_app,
        # router=app.router
        # router=router
    )
    catalog_app.state.router_prefix = f"{root_path}/catalogs/{catalog}"
    catalog_app.router.prefix = f"{root_path}/catalogs/{catalog}"

    # catalog_app = api.app

    # catalog_app = api.app
    # router = catalog_app.router
    # app.router.include_router(prefix=f"{root_path}/catalogs/{catalog}", router=catalog_app.router)

    # router.prefix = root_path
    # for route in router.routes:
    #     print(f"{root_path}/catalogs/{catalog}{route.path}")
    #     app.add_route(path=f"{root_path}/catalogs/{catalog}{route.path}", route=route)
    app.mount(path=f"{root_path}/catalogs/{catalog}", app=catalog_app)


# Add rate limit
setup_rate_limit(app, rate_limit=os.getenv("STAC_FASTAPI_RATE_LIMIT"))


@app.on_event("startup")
async def _startup_event() -> None:
    await create_index_templates()
    await create_collection_index()


# @app.get("/app")
# def read_main():
#     return {"message": "Hello World from main app"}


# main_app.mount("/main_app", app)


def run() -> None:
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "stac_fastapi.elasticsearch.app:app",
            # "stac_fastapi.elasticsearch.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    print("something")
    run()


def create_handler(app):
    """Create a handler to use with AWS Lambda if mangum available."""
    try:
        from mangum import Mangum

        return Mangum(app)
    except ImportError:
        return None


handler = create_handler(app)
