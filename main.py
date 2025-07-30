from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI #for OpenAI LLM
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from dotenv import load_dotenv
import os
import asyncio
from pyvis.network import Network

load_dotenv()

openAI_api_key = os.getenv("OPENAI_API_KEY")
gemini_api_key = os.getenv("GOOGLE_API_KEY")

def get_llm():
    """Get LLM instance - synchronous initialization"""
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash")

def initialize_graph_transformer(llm, nodes: list = [], relationships: list = []):
    """
    Initialize graph transformer synchronously to avoid async issues
    """
    try:
        if nodes and relationships:
            graph_transformer = LLMGraphTransformer(llm=llm, allowed_nodes=nodes, allowed_relationships=relationships)
        elif nodes:
            graph_transformer = LLMGraphTransformer(llm=llm, allowed_nodes=nodes)
        elif relationships:
            graph_transformer = LLMGraphTransformer(llm=llm, allowed_relationships=relationships)
        else:
            graph_transformer = LLMGraphTransformer(llm=llm)
        return graph_transformer
    except Exception as e:
        print(f"Failed to initialize Graph Transformer due to: {e}")
        return None

async def extract_graph_data(text, graph_transformer):
    """
    Asynchronously extracts graph data from input text using a graph transformer.

    Args:
        text (str): Input text to be processed into graph format.
        graph_transformer: The initialized graph transformer

    Returns:
        list: A list of GraphDocument objects containing nodes and relationships.
    """
    try:
        documents = [Document(page_content=text)]
        graph_documents = await graph_transformer.aconvert_to_graph_documents(documents)
        return graph_documents
    except Exception as e:
        print(f"Error extracting graph data: {e}")
        return None

def visualize_graph(graph_documents):
    """
    Visualizes a knowledge graph using PyVis based on the extracted graph documents.

    Args:
        graph_documents (list): A list of GraphDocument objects with nodes and relationships.

    Returns:
        pyvis.network.Network: The visualized network graph object.
    """
    if not graph_documents:
        print("No graph documents to visualize")
        return None
        
    # Create network
    net = Network(height="1200px", width="100%", directed=True,
                  notebook=False, bgcolor="#222222", font_color="white", 
                  filter_menu=True, cdn_resources='remote') 

    nodes = graph_documents[0].nodes
    relationships = graph_documents[0].relationships

    # Build lookup for valid nodes
    node_dict = {node.id: node for node in nodes}
    
    # Filter out invalid edges and collect valid node IDs
    valid_edges = []
    valid_node_ids = set()
    for rel in relationships:
        if rel.source.id in node_dict and rel.target.id in node_dict:
            valid_edges.append(rel)
            valid_node_ids.update([rel.source.id, rel.target.id])

    # Add valid nodes to the graph
    for node_id in valid_node_ids:
        node = node_dict[node_id]
        try:
            net.add_node(node.id, label=node.id, title=node.type, group=node.type)
        except Exception as e:
            print(f"Error adding node {node_id}: {e}")
            continue

    # Add valid edges to the graph
    for rel in valid_edges:
        try:
            net.add_edge(rel.source.id, rel.target.id, label=rel.type.lower())
        except Exception as e:
            print(f"Error adding edge {rel.source.id} -> {rel.target.id}: {e}")
            continue

    # Configure graph layout and physics
    net.set_options("""
        {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -100,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08
                },
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based"
            }
        }
    """)

    return net

async def generate_knowledge_graph_async(text, graph_transformer):
    """
    Generates and visualizes a knowledge graph from input text asynchronously.

    Args:
        text (str): Input text to convert into a knowledge graph.
        graph_transformer: The initialized graph transformer

    Returns:
        pyvis.network.Network: The visualized network graph object.
    """
    try:
        graph_documents = await extract_graph_data(text, graph_transformer)
        if graph_documents:
            net = visualize_graph(graph_documents)
            return net, graph_documents
        return None, None
    except Exception as e:
        print(f"Error generating knowledge graph: {e}")
        return None, None