# Import necessary modules
import streamlit as st
import streamlit.components.v1 as components  # For embedding custom HTML
from main import generate_knowledge_graph_async, initialize_graph_transformer, extract_graph_data, get_llm
from langchain_core.documents import Document
import asyncio
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Set up Streamlit page configuration
st.set_page_config(
    page_icon=None, 
    layout="wide",  # Use wide layout for better graph display
    initial_sidebar_state="auto", 
    menu_items=None
)

# Set the title of the app
st.title("Knowledge Graph From Text")

# Sidebar section for user input method
st.sidebar.title("Input document")
input_method = st.sidebar.radio(
    "Choose an input method:",
    ["Upload file", "Input text"],  # Options for uploading a file or manually inputting text
)

# Add options for showing nodes and relationships
st.sidebar.markdown("---")
st.sidebar.title("Display Options")
show_nodes = st.sidebar.checkbox("Show extracted nodes", value=False)
show_relationships = st.sidebar.checkbox("Show extracted relationships", value=False)

# Add options for custom nodes and relationships
st.sidebar.markdown("---")
st.sidebar.title("Custom Graph Configuration")
use_custom_nodes = st.sidebar.checkbox("Use custom nodes", value=False)
use_custom_relationships = st.sidebar.checkbox("Use custom relationships", value=False)

custom_nodes = []
custom_relationships = []

if use_custom_nodes:
    custom_nodes_input = st.sidebar.text_area(
        "Enter custom nodes (comma-separated):",
        placeholder="Person, Organization, Location, Event",
        help="Specify the types of nodes you want to extract from the text"
    )
    if custom_nodes_input.strip():
        custom_nodes = [node.strip() for node in custom_nodes_input.split(",") if node.strip()]
        st.sidebar.info(f"Custom nodes: {', '.join(custom_nodes)}")

if use_custom_relationships:
    custom_relationships_input = st.sidebar.text_area(
        "Enter custom relationships (comma-separated):",
        placeholder="WORKS_FOR, LOCATED_IN, MARRIED_TO, MEMBER_OF",
        help="Specify the types of relationships you want to extract from the text"
    )
    if custom_relationships_input.strip():
        custom_relationships = [rel.strip() for rel in custom_relationships_input.split(",") if rel.strip()]
        st.sidebar.info(f"Custom relationships: {', '.join(custom_relationships)}")

# Character limit constant
CHAR_LIMIT =int(os.getenv("CHAR_LIMIT"))


def truncate_text(text, limit=CHAR_LIMIT):
    """Truncate text to specified character limit"""
    if len(text) > limit:
        return text[:limit]
    return text

def display_nodes_and_relationships(graph_documents):
    """Display nodes and relationships in a structured format"""
    if not graph_documents:
        return
    
    nodes = graph_documents[0].nodes
    relationships = graph_documents[0].relationships
    
    if show_nodes and nodes:
        st.subheader("Extracted Nodes")
        node_data = []
        for node in nodes:
            node_data.append({
                "Node ID": node.id,
                "Type": node.type,
                "Properties": str(node.properties) if hasattr(node, 'properties') else "N/A"
            })
        
        nodes_df = pd.DataFrame(node_data)
        st.dataframe(nodes_df, use_container_width=True)
        
        # Download nodes as CSV
        csv_nodes = nodes_df.to_csv(index=False)
        st.download_button(
            label="Download nodes as CSV",
            data=csv_nodes,
            file_name="knowledge_graph_nodes.csv",
            mime="text/csv"
        )
    
    if show_relationships and relationships:
        st.subheader("Extracted Relationships")
        rel_data = []
        for rel in relationships:
            rel_data.append({
                "Source": rel.source.id,
                "Relationship": rel.type,
                "Target": rel.target.id,
                "Properties": str(rel.properties) if hasattr(rel, 'properties') else "N/A"
            })
        
        rels_df = pd.DataFrame(rel_data)
        st.dataframe(rels_df, use_container_width=True)
        
        # Download relationships as CSV
        csv_rels = rels_df.to_csv(index=False)
        st.download_button(
            label="Download relationships as CSV",
            data=csv_rels,
            file_name="knowledge_graph_relationships.csv",
            mime="text/csv"
        )

async def process_text_async(text, custom_nodes=None, custom_relationships=None):
    """Async function to process text and extract graph data"""
    try:
        # Initialize LLM
        llm = get_llm()
        
        # Initialize graph transformer with custom nodes and relationships if provided
        nodes_list = custom_nodes if custom_nodes else []
        relationships_list = custom_relationships if custom_relationships else []
        
        graph_transformer = initialize_graph_transformer(llm, nodes_list, relationships_list)
        
        if graph_transformer is None:
            return None, None
        
        # Generate knowledge graph and get graph documents
        net, graph_documents = await generate_knowledge_graph_async(text, graph_transformer)
        return graph_documents, net
        
    except Exception as e:
        print(f"Error in process_text_async: {e}")
        return None, None

def extract_text(uploaded_file):
    """Extract text from uploaded file based on file type"""
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            # For PDF files, you'll need to use your FileParser
            st.sidebar.warning("PDF processing requires the FileParser utility. Using basic text extraction.")
            return uploaded_file.read().decode("utf-8", errors='ignore')
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            st.sidebar.warning("DOCX processing requires additional libraries. Please convert to txt first.")
            return None
        elif uploaded_file.type == "application/vnd.ms-powerpoint" or uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            st.sidebar.warning("PPT processing requires additional libraries. Please convert to txt first.")
            return None
        else:
            # Try to read as text
            return uploaded_file.read().decode("utf-8", errors='ignore')
    except Exception as e:
        st.sidebar.error(f"Error extracting text from file: {str(e)}")
        return None

# Function to handle graph generation for both file upload and text input
def handle_graph_generation(text):
    """Handle the graph generation process"""
    if len(text.strip()) > 0 and len(text) <= CHAR_LIMIT:
        with st.spinner("Generating knowledge graph..."):
            try:
                # Process text asynchronously to get graph documents with custom parameters
                graph_documents, net = asyncio.run(process_text_async(text, custom_nodes, custom_relationships))
                
                if graph_documents and net:
                    # Display nodes and relationships if requested
                    display_nodes_and_relationships(graph_documents)
                    
                    st.success("Knowledge graph generated successfully!")
                    
                    # Save the graph to an HTML file
                    output_file = "knowledge_graph.html"
                    net.save_graph(output_file) 

                    # Display graph statistics
                    nodes = graph_documents[0].nodes
                    relationships = graph_documents[0].relationships
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Nodes", len(nodes))
                    with col2:
                        st.metric("Total Relationships", len(relationships))
                    with col3:
                        st.metric("Text Length", f"{len(text):,} chars")

                    # Show custom configuration if used
                    if custom_nodes or custom_relationships:
                        st.info(f"Used custom nodes: {custom_nodes if custom_nodes else 'Default'} | Custom relationships: {custom_relationships if custom_relationships else 'Default'}")

                    # Open the HTML file and display it within the Streamlit app
                    with open(output_file, 'r', encoding='utf-8') as HtmlFile:
                        components.html(HtmlFile.read(), height=1000)
                        
                else:
                    st.error("Failed to generate graph documents. Please check your API keys and try again.")
                    
            except Exception as e:
                st.error(f"Error generating knowledge graph: {str(e)}")
                print(f"Detailed error: {e}")
    else:
        if len(text.strip()) == 0:
            st.sidebar.error("Please enter some text.")
        elif len(text) > CHAR_LIMIT:
            st.sidebar.error(f"Text exceeds the {CHAR_LIMIT:,} character limit.")

# Case 1: User chooses to upload a file
if input_method == "Upload file":
    # File uploader widget in the sidebar - support multiple file types
    uploaded_file = st.sidebar.file_uploader(
        label="Upload file", 
        type=["txt", "pdf", "docx", "ppt"]
    )
    
    if uploaded_file is not None:
        try:
            text = extract_text(uploaded_file)
            
            if text:
                # Check character limit
                original_length = len(text)
                text = truncate_text(text)
                
                if original_length > CHAR_LIMIT:
                    st.sidebar.warning(f"Text truncated from {original_length:,} to {CHAR_LIMIT:,} characters due to processing limits.")
                
                st.sidebar.success(f"File loaded successfully! ({len(text):,} characters)")
                
                # Show text preview
                with st.sidebar.expander("Preview text"):
                    st.text(text[:500] + "..." if len(text) > 500 else text)
            else:
                st.sidebar.error("Could not extract text from the uploaded file.")
                text = None
                
        except Exception as e:
            st.sidebar.error(f"Error reading file: {str(e)}")
            text = None
        
        # Button to generate the knowledge graph
        if uploaded_file is not None and text and st.sidebar.button("Generate Knowledge Graph"):
            handle_graph_generation(text)

# Case 2: User chooses to directly input text
else:
    # Text area for manual input
    text = st.sidebar.text_area("Input text", height=300, max_chars=CHAR_LIMIT)
    
    # Show character count
    if text:
        char_count = len(text)
        st.sidebar.info(f"Characters: {char_count:,} / {CHAR_LIMIT:,}")
        
        if char_count > CHAR_LIMIT:
            st.sidebar.error(f"Text exceeds the {CHAR_LIMIT:,} character limit. Please reduce the text length.")
    
    # Button to generate the knowledge graph
    if text and st.sidebar.button("Generate Knowledge Graph"):
        handle_graph_generation(text)

# Add footer with instructions
st.markdown("---")
st.markdown("""
### Instructions:
1. Choose to upload a file or input text manually
2. Optionally enable display of extracted nodes and relationships
3. Click 'Generate Knowledge Graph' to create and visualize your graph
4. The graph will be displayed below with interactive features

**Note:** Text input is limited to 25,000 characters for optimal processing performance.
""")