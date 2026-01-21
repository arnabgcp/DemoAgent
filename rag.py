import os

from google import genai
from google.cloud import aiplatform

PROJECT_ID = "[your-project-id]"  # @param {type: "string", placeholder: "[your-project-id]", isTemplate: true}
if not PROJECT_ID or PROJECT_ID == "[your-project-id]":
    PROJECT_ID = str(os.environ.get("GOOGLE_CLOUD_PROJECT"))

LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "europe-west3")

aiplatform.init(project=PROJECT_ID, location=LOCATION)
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# my_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
#    display_name="Arnab-Index-eu",
#    description="test rag",
#    dimensions=768,
#    approximate_neighbors_count=10,
#    leaf_node_embedding_count=500,
#    leaf_nodes_to_search_percent=7,
#    distance_measure_type="DOT_PRODUCT_DISTANCE",
#    feature_norm_type="UNIT_L2_NORM",
#    index_update_method="STREAM_UPDATE",
# )



# my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
#    display_name="Arnab-endpoint-eu", public_endpoint_enabled=True
# )


my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.list()[0]


my_index = aiplatform.MatchingEngineIndex('3352797981182001152')

# my_index_endpoint.deploy_index(
#     index=my_index, deployed_index_id="v1"
# )

from google.genai.types import (
    GenerateContentConfig,
    Retrieval,
    Tool,
    VertexRagStore,
    VertexRagStoreRagResource,
)
from vertexai import rag

# vector_db = rag.VertexVectorSearch(
#     index=my_index.resource_name, index_endpoint=my_index_endpoint.resource_name
# )

# Name your corpus
# DISPLAY_NAME = "arnab-corpus-eu"  # @param  {type:"string"}

# # Create RAG Corpus
# rag_corpus = rag.create_corpus(
#     display_name=DISPLAY_NAME, backend_config=rag.RagVectorDbConfig(vector_db=vector_db)
# )
# print(f"Created RAG Corpus resource: {rag_corpus.name}")

# print(my_index.resource_name)

rag_corpus = rag.get_corpus(name="projects/wayfair-test-378605/locations/europe-west3/ragCorpora/6917529027641081856")

# GCS_BUCKET = "gs://rag-bucket-test-cases/"  # @param {type:"string", "placeholder": "your-gs-bucket"}

# response = rag.import_files(  # noqa: F704
#     corpus_name=rag_corpus.name,
#     paths=[GCS_BUCKET],
#     transformation_config=rag.TransformationConfig(
#         chunking_config=rag.ChunkingConfig(
#             chunk_size=512,
#             chunk_overlap=50,
#         )
#     ),
# )

# FILE_ID = "1nasWou9StYT06PHUscF095r5FNJGY36wPBiqLqWh3Pk"  # @param {type:"string", "placeholder": "your-file-id"}
# FILE_PATH = f"https://drive.google.com/file/d/{FILE_ID}"

# # https://drive.google.com/file/d/1nasWou9StYT06PHUscF095r5FNJGY36wPBiqLqWh3Pk



# rag.import_files(
#     corpus_name=rag_corpus.name,
#     paths=[FILE_PATH],
#     transformation_config=rag.TransformationConfig(
#         chunking_config=rag.ChunkingConfig(
#             chunk_size=1024,
#             chunk_overlap=100,
#         )
#     ),
# )


MODEL_ID = "gemini-2.5-flash"

rag_retrieval_tool = Tool(
    retrieval=Retrieval(
        vertex_rag_store=VertexRagStore(
            rag_resources=[
                VertexRagStoreRagResource(
                    rag_corpus=rag_corpus.name  # Currently only 1 corpus is allowed.
                )
            ],
            similarity_top_k=10,
            vector_distance_threshold=0.4,
        )
    )
)


GENERATE_CONTENT_PROMPT = "how to scale up finance appd?"  # @param {type:"string"}

response = client.models.generate_content(
    model=MODEL_ID,
    contents=GENERATE_CONTENT_PROMPT,
    config=GenerateContentConfig(tools=[rag_retrieval_tool]),
)

print(response.text)

